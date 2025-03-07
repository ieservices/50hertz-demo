import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);

  // Funktion zum Abruf des EMS-Status von der FastAPI
  const fetchStatus = async () => {
    try {
      const apiBaseUrl = process.env.REACT_APP_API_URL || "http://localhost:8000";
      const endpoint = `${apiBaseUrl}/get_status`;
      const response = await fetch(endpoint);
      if (!response.ok) {
        throw new Error("Netzwerkantwort war nicht ok");
      }
      const data = await response.json();
      setStatus(data);
    } catch (err) {
      console.error("Fehler beim Abrufen des Status:", err);
      setError("Fehler beim Abrufen des Status");
    }
  };

  useEffect(() => {
    // Initialen Abruf durchführen
    fetchStatus();
    // Alle 1000ms den Status abrufen
    const interval = setInterval(() => {
      fetchStatus();
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  if (error) {
    return <div>{error}</div>;
  }

  if (!status) {
    return <div>Lade Status...</div>;
  }

  return (
    <div className="App">
      <h1>50hertz Demo EMS Status Dashboard</h1>
      <div className="status-card">
        <p><strong>Aktueller Strompreis:</strong> {status.current_price} ct (€)</p>
        <p><strong>Status:</strong> {status.charging}</p>
        <p><strong>Batteriekapazität:</strong> {status.battery_capacity_kwh} kWh</p>
        <p><strong>Batteriekapazität (%):</strong> {status.battery_capacity_percent} %</p>
        <p><strong>Verbrauchsrate der Anlage:</strong> {status.facility_consumption_rate} kWh/s</p>
        <p><strong>Gesamter Verbrauch:</strong> {status.total_consumption_kwh} kWh</p>
      </div>
      <footer className="footer">Demo für 50hertz</footer>
    </div>
  );
}

export default App;
