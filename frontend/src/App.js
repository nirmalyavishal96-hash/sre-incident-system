import React, { useEffect, useState } from "react";

function App() {
  const [incidents, setIncidents] = useState([]);
  const [selected, setSelected] = useState(null);
  const [rca, setRca] = useState({ root_cause: "", fix: "" });

  const fetchIncidents = async () => {
    const res = await fetch("http://127.0.0.1:8000/incidents");
    const data = await res.json();

    // Sort: OPEN first, CLOSED last
    data.sort((a, b) => {
      if (a.status === "OPEN" && b.status !== "OPEN") return -1;
      if (a.status !== "OPEN" && b.status === "OPEN") return 1;
      return a.id - b.id;
    });

    setIncidents(data);
  };

  useEffect(() => {
    fetchIncidents();
  }, []);

  const selectIncident = (incident) => {
    setSelected(incident);
    setRca({ root_cause: "", fix: "" }); // reset RCA form
  };

  const updateStatus = async (status) => {
    await fetch(`http://127.0.0.1:8000/incidents/${selected.id}/status`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });

    await fetchIncidents();
  };

  const submitRCA = async () => {
    await fetch(`http://127.0.0.1:8000/incidents/${selected.id}/rca`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(rca),
    });

    setRca({ root_cause: "", fix: "" });
    await fetchIncidents();
  };

  return (
    <div style={{ padding: 20 }}>
      <h1> Incident Dashboard</h1>

      <h2>Incidents</h2>

      {incidents.map((i) => (
        <div
          key={i.id}
          onClick={() => selectIncident(i)}
          style={{
            border: "1px solid black",
            margin: 10,
            padding: 10,
            cursor: "pointer",
            backgroundColor: i.status === "CLOSED" ? "#d4edda" : "#fff3cd",
          }}
        >
          <p><strong>ID:</strong> {i.id}</p>
          <p><strong>Component:</strong> {i.component}</p>
          <p><strong>Status:</strong> {i.status}</p>
          <p><strong>MTTR:</strong> {i.mttr_seconds || "N/A"}</p>
        </div>
      ))}

      {selected && (
        <div style={{ marginTop: 20 }}>
          <h2>Incident Details</h2>

          <p><strong>ID:</strong> {selected.id}</p>
          <p><strong>Status:</strong> {selected.status}</p>

          {/* RCA status indicator */}
          <p>
            <strong>RCA Status:</strong>{" "}
            {selected.status === "CLOSED" ? "Available " : "Not Added ❌"}
          </p>

          {/* Status buttons */}
          <div style={{ marginTop: 10 }}>
            <button onClick={() => updateStatus("INVESTIGATING")}>
              Investigate
            </button>

            <button onClick={() => updateStatus("RESOLVED")}>
              Resolve
            </button>

            {/* Disable close if RCA not filled */}
            <button
              onClick={() => updateStatus("CLOSED")}
              disabled={!rca.root_cause || !rca.fix}
            >
              Close
            </button>
          </div>

          {/* RCA Form */}
          <h3>RCA</h3>

          <input
            placeholder="Root Cause"
            value={rca.root_cause}
            onChange={(e) =>
              setRca({ ...rca, root_cause: e.target.value })
            }
          />
          <br />

          <input
            placeholder="Fix"
            value={rca.fix}
            onChange={(e) => setRca({ ...rca, fix: e.target.value })}
          />
          <br />

          <button onClick={submitRCA}>Submit RCA</button>
        </div>
      )}
    </div>
  );
}

export default App;