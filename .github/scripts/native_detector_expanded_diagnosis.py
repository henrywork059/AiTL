"""Read-only postmortem of the frozen expanded development evidence.

No inference, changed matching rules, training, or controller authority.
Replay is counterfactual, using retained service times, not live delivery.
"""
import argparse
from collections import Counter
import hashlib
import io
import json
import math
from pathlib import Path
from zipfile import ZipFile

CAPTURE_SHA = '305dfc47e1ef2d8fb70ff6aa069c0d5cc89cd688c129c2e457a4337e41b46dd1'
DETECTOR_SHA = '4fe924271fd3d7ef41437a3d80655fa161e9dc023a97e22b0771bcdf0d1ee8d5'
KINDS = ('vehicle', 'pedestrian')
SEEDS = (1103, 1201, 1301, 1409)


def center(box):
    l,t,r,b = box
    return ((l+r)/2, (t+b)/2)


def intersects(a,b):
    return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])


def inside(point,zone):
    x,y=point
    return zone[0]<=x<zone[2] and zone[1]<=y<zone[3]


def native_centers(scene,kind):
    return {a['id']:(a['x']+((-1 if a['eastbound'] else 1)*a['length_m']*scene['pixels_per_m']/2
                    if kind=='vehicle' else 0),a['y']) for a in scene['agents'] if a['kind']==kind}


def event_status(a,b,crossing_ids):
    if not a or not b:
        return 'endpoint_missing_iou_match'
    if len(a)!=1 or len(b)!=1:
        return 'ambiguous_center_track'
    if a!=b:
        return 'different_track_ids'
    return 'same_track_crossing_in_bracket' if a[0] in crossing_ids else 'same_track_no_crossing_in_bracket'


def latest_frame_replay(times,durations):
    """Nonpreemptive service, latest available frame when idle; no future lookahead."""
    if not times or len(times)!=len(durations) or any(b<=a for a,b in zip(times,times[1:])) or any(not math.isfinite(v) or v<0 for v in durations):
        raise ValueError('Invalid replay inputs')
    done=0.;i=0;served=[];dropped=[]
    while i<len(times):
        start=max(done,times[i]);j=i
        while j+1<len(times) and times[j+1]<=start:
            j+=1
        dropped.extend(range(i,j));done=start+durations[j]
        served.append({'index':j,'start_ms':start,'age_ms':done-times[j]});i=j+1
    return served,dropped


def analyze_class(frames,scenes,run,kind):
    zone=run['zone'];r=run['metrics'][kind];sup=run['supplementary'][kind]
    native_counts=sup['native_center_sensitivity']['truth_counts'];pred_counts=r['predicted_counts']
    pairs=[];counts=Counter();unmatched=[];errors=[]
    for i,(f,s) in enumerate(zip(frames,scenes)):
        truth={a['agent_id']:a['box_xyxy'] for a in f['truth'] if a['kind']==kind}
        pts=native_centers(s,kind)
        pred={j:p for j,p in enumerate(f['predictions']) if p['kind']==kind}
        matched={m['agent_id']:m['prediction_index'] for m in f['score']['matches'] if m['agent_id'] in truth}
        if set(pts)!=set(truth) or len(set(matched.values()))!=len(matched) or not set(matched.values())<=set(pred):
            raise ValueError('Invalid frozen identity matches')
        tracks=r['tracks'][i]['prediction_tracks']
        pairs.append({a:[tid for tid,xy in tracks.items() if tuple(xy)==center(pred[j]['box_xyxy'])] for a,j in matched.items()})
        a=Counter()
        for ident,p in pts.items():
            if ident not in matched:
                a['unmatched_truth_inside']+=inside(p,zone)
            else:
                b=inside(center(pred[matched[ident]]['box_xyxy']),zone);g=inside(p,zone)
                a['matched_boundary_in']+=b and not g;a['matched_boundary_out']+=g and not b
        for j,p in pred.items():
            if j in matched.values() or not inside(center(p['box_xyxy']),zone):
                continue
            a['unmatched_prediction_inside']+=1
            overlaps=[ident for ident,b in truth.items() if intersects(b,p['box_xyxy'])]
            a['unmatched_inside_overlaps_matched_truth']+=any(k in matched for k in overlaps)
            a['unmatched_inside_no_truth_overlap']+=not overlaps
            unmatched.append({'sample':i,'prediction_index':j,'box':p['box_xyxy'],'tile_index':p['tile_index'],
                              'confidence':p['confidence'],'truth_overlap_ids':overlaps})
        delta=pred_counts[i]-native_counts[i]
        if (sum(inside(p,zone) for p in pts.values())!=native_counts[i] or
            sum(inside(center(p['box_xyxy']),zone) for p in pred.values())!=pred_counts[i] or
            delta!=a['unmatched_prediction_inside']-a['unmatched_truth_inside']+a['matched_boundary_in']-a['matched_boundary_out']):
            raise ValueError('Frozen occupancy decomposition mismatch')
        counts.update(a);counts['net_count_error']+=delta;counts['absolute_count_error']+=abs(delta)
        counts['overcount_samples']+=delta>0;counts['undercount_samples']+=delta<0
        if delta:
            errors.append({'sample':i,'delta':delta,**dict(a)})
    e=sup['every_tick_native_passages'];missed=set(e['missed']);matched_events=dict(e['matches']);stats=Counter();rows=[]
    for n,v in enumerate(e['truth']):
        i=math.ceil(v['stop_ms']/400);ident=v['id'];a=pairs[i-1].get(ident,[]);b=pairs[i].get(ident,[])
        def crossings(j):
            return [str(q['id']) for q in e['predicted'] if q['direction']==v['direction'] and q['start_ms']==(j-1)*400 and q['stop_ms']==j*400]
        status=event_status(a,b,crossings(i));adj=[]
        for j in (i-1,i+1):
            if 1<=j<len(frames):
                aa=pairs[j-1].get(ident,[]);bb=pairs[j].get(ident,[])
                if len(aa)==len(bb)==1 and aa==bb and aa[0] in crossings(j):
                    adj.append({'start_ms':(j-1)*400,'stop_ms':j*400,'track_id':aa[0]})
        confirmed=n in matched_events and len(a)==len(b)==1 and a==b and str(e['predicted'][matched_events[n]]['id'])==a[0]
        stats['missed_'+status if n in missed else 'matched_identity_supported' if confirmed else 'matched_identity_unconfirmed']+=1
        if n in missed and adj:
            stats['missed_with_adjacent_identity_supported_crossing']+=1
        rows.append({'event_index':n,'event':v,'frozen_missed':n in missed,'status':status,'endpoint_tracks':[a,b],
                     'frozen_match_identity_supported':confirmed,'adjacent_crossings':adj})
    return {'count_decomposition':dict(counts),'count_errors':errors,'unmatched_inside':unmatched,
            'event_diagnostics':dict(stats),'events':rows}


def review(capture_path,detector_path):
    from PIL import Image
    inputs=[p.read_bytes() for p in (capture_path,detector_path)]
    if [hashlib.sha256(b).hexdigest() for b in inputs]!=[CAPTURE_SHA,DETECTOR_SHA]:
        raise ValueError('Only the exact audited development artifacts are admitted')
    result={'capture_sha256':CAPTURE_SHA,'detector_sha256':DETECTOR_SHA,'formal_holdout_used':False,
            'absolute_qualification':False,'physical_output_allowed':False,'runs':[]}
    with ZipFile(io.BytesIO(inputs[0])) as c, ZipFile(io.BytesIO(inputs[1])) as z:
        report=json.loads(z.read('temporal-evidence/report.json'))
        if any(report[k] is not False for k in ('formal_holdout_used','absolute_qualification','physical_output_allowed')) or [r['seed'] for r in report['runs']]!=list(SEEDS):
            raise ValueError('Unexpected evidence scope')
        for run in report['runs']:
            seed=run['seed'];frames=[json.loads(l) for l in z.read(f'temporal-evidence/frames-{seed}.jsonl').splitlines()]
            scenes=[json.loads(l) for l in c.read(f'{seed}/native-ticks.jsonl').splitlines()][::2]
            times=[f['time_ms'] for f in frames]
            if times!=list(range(0,120001,400)) or [s['tick'] for s in scenes]!=list(range(0,601,2)):
                raise ValueError('Incomplete frame schedule')
            classes={k:analyze_class(frames,scenes,run,k) for k in KINDS}
            for row in classes['vehicle']['unmatched_inside']:
                f=frames[row['sample']]
                raw=c.read(f['capture'])
                if hashlib.sha256(raw).hexdigest()!=f['archive_sha256']:
                    raise ValueError('Capture mismatch')
                with ZipFile(io.BytesIO(raw)) as a:
                    image=Image.open(io.BytesIO(a.read('simulation_camera.png'))).convert('RGB')
                    colors=Counter(image.crop(row['box']).getdata())
                row['crossing_gray_fraction']=colors[(225,225,225)]/sum(colors.values())
                row['modal_rgb']=list(colors.most_common(1)[0][0]);row['blue_dominant_pixels']=sum(n for (r,g,b),n in colors.items() if b>r+50 and b>g+30)
            served,dropped=latest_frame_replay(times,[f['inference_ms'] for f in frames])
            timely={s['index'] for s in served if s['age_ms']<=400}
            result['runs'].append({'seed':seed,'classes':classes,'counterfactual_latest_frame':{
                'served':served,'dropped_indices':dropped,'timely_count':len(timely),
                'timely_correct_occupied':{k:sum(i in timely and t>0 and p>0 for i,(t,p) in enumerate(zip(
                    run['supplementary'][k]['native_center_sensitivity']['truth_counts'],run['metrics'][k]['predicted_counts']))) for k in KINDS}}})
    return result


def self_test():
    assert event_status([],['1'],[])=='endpoint_missing_iou_match'
    assert event_status(['1','2'],['1'],[])=='ambiguous_center_track'
    assert event_status(['1'],['2'],['2'])=='different_track_ids'
    assert event_status(['1'],['1'],['1'])=='same_track_crossing_in_bracket'
    assert event_status(['1'],['1'],[])=='same_track_no_crossing_in_bracket'
    s,d=latest_frame_replay([0,400,800,1200],[1000,10,100,100])
    assert d==[1] and [(x['index'],x['age_ms']) for x in s]==[(0,1000),(2,300),(3,100)]
    assert not intersects([0,0,1,1],[1,0,2,1]) and intersects([0,0,2,2],[1,1,3,3])
    assert inside((0,0),[0,0,1,1]) and not inside((1,1),[0,0,1,1])
    print('Expanded diagnosis deterministic checks passed')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--self-test',action='store_true')
    for name in ('captures','detector','output'):
        p.add_argument('--'+name,type=Path)
    a=p.parse_args()
    if a.self_test:
        self_test()
    else:
        if not all((a.captures,a.detector,a.output)) or a.output.exists():
            p.error('Exact input archives and a new output path are required')
        data=review(a.captures,a.detector)
        with a.output.open('x',encoding='utf-8') as f:
            json.dump(data,f,indent=2,allow_nan=False)
