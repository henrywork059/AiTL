import {useState} from "react";
import {NativeProjectionView} from "../components/NativeProjectionView";
const views=["simulation_camera","simulation_camera_b","simulation_camera_c","simulation_camera_d"];
/** Independent native workspace; shares the same native service, not camera selection. */
export function NativeSimulationWorkspace({profile}:{profile?:string}){
  const [source,setSource]=useState(views[0]);
  return <div className="native-lab-workspace">
    <div className="experiment-header"><div><h2>Native SUMO evaluation</h2><p className="placeholder-copy">Independent synthetic simulation. Saved camera and legacy region coordinates remain unchanged. Comparison ZIP uses one saved signal policy copy ({profile||"active profile"}).</p></div>
      <label>View <select value={source} onChange={e=>setSource(e.target.value)}>{views.map((v,i)=><option key={v} value={v}>{["A","B","C","D"][i]}</option>)}</select></label></div>
    <div className="sim3d-viewport native-lab-preview" data-native-lab="true"><NativeProjectionView sourceId={source} standaloneOnly profile={profile}/></div>
    <p className="placeholder-copy">Native metrics are normalized gate measurements, not production legacy per-visit metrics. Stop native evaluation before comparing policies. Switching views retires client playback and the previous snapshot; explicitly stop to release the native session.</p>
  </div>;
}
