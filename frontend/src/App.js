import React, { useEffect, useState } from "react";

const API_URL = "http://localhost:8000";

function App() {
  const [incidents, setIncidents] = useState([]);
  const [selected, setSelected] = useState(null);
  const [rca, setRca] = useState({ root_cause: "", fix: "" });

  // Fetch incidents
  const fetchIncidents = async () => {
    try {
      const res = await fetch(`${API_URL}/incidents`);
      const data = await res.json();

      // Sort: OPEN first
      data.sort((a, b) => {
        if (a.status === "OPEN" && b.status !== "OPEN") return -1;
        if (a.status !== "OPEN" && b.status === "OPEN") return 1;
        return a.id - b.id;
      });

      setIncidents(data);

      // Keep selected incident updated
      if (selected) {
        const updated = data.find((i) => i.id === selected.id);
        setSelected(updated);
      }

    } catch (err) {
      console.error("Error fetching incidents:", err);
    }
  };

  //  Auto refresh every 5 sec (important)
  useEffect(() => {
    fetchIncidents();

    const interval = setInterval(() => {
      fetchIncidents();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const selectIncident = (incident) => {
    setSelected(incident);
    setRca({ root_cause: "", fix: "" });
  };

  const updateStatus = async (status) => {
    try {
      await fetch(`${API_URL}/incidents/${selected.id}/status`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });

      await fetchIncidents();
    } catch (err) {
      console.error("Error updating status:", err);
    }
  };

  const submitRCA = async () => {
    try {
      await fetch(`${API_URL}/incidents/${selected.id}/rca`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(rca),
      });

      setRca({ root_cause: "", fix: "" });
      await fetchIncidents();
    } catch (err) {
      console.error("Error submitting RCA:", err);
    }
  };

  return (
    <div style={{ padding: 20 }}>
      <h1>Incident Dashboard</h1>

      <h2>Incidents</h2>

      {incidents.length === 0 && <p>No incidents yet...</p>}

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
          <p><strong>MTTR:</strong> {i.mttr_seconds ? i.mttr_seconds.toFixed(2) : "N/A"}</p>
        </div>
      ))}

      {selected && (
        <div style={{ marginTop: 20 }}>
          <h2>Incident Details</h2>

          <p><strong>ID:</strong> {selected.id}</p>
          <p><strong>Status:</strong> {selected.status}</p>

          <p>
            <strong>RCA Status:</strong>{" "}
            {selected.status === "CLOSED" ? "Available " : "Not Added"}
          </p>

          <div style={{ marginTop: 10 }}>
            <button onClick={() => updateStatus("INVESTIGATING")}>
              Investigate
            </button>

            <button onClick={() => updateStatus("RESOLVED")}>
              Resolve
            </button>

            <button
              onClick={() => updateStatus("CLOSED")}
              disabled={!rca.root_cause || !rca.fix}
            >
              Close
            </button>
          </div>

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