import { useApp } from "../../state_imp/AppContext";


export default function EmergencyPanel() {
  const { state } = useApp();

  return (
    <div>
      <h3>Traveller</h3>
      <div style={{ fontWeight: 700 }}>Emergency active</div>
      <div>Support team is stepping in.</div>

      {/* later: chat forced open, recording indicator */}
      <div>Live Eye + Human takeover will show here.</div>
    </div>
  );
}
