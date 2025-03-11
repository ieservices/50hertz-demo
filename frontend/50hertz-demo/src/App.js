import React, {useState, useEffect} from "react";

function StatusWebSocket() {
    const [status, setStatus] = useState(null);
    const [error, setError] = useState(null);
    const apiBaseUrl = process.env.REACT_APP_API_URL || 'ws://localhost:8000';

    useEffect(() => {
        const ws = new WebSocket(`${apiBaseUrl}/ws/status`);

        ws.onopen = () => {
            console.log("WebSocket connection opened");
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                setError(null);
                setStatus(data);
            } catch (e) {
                console.error("Error parsing message", e);
            }
        };

        ws.onerror = (err) => {
            console.error("WebSocket error", err);
            setError("WebSocket error");
        };

        ws.onclose = () => {
            console.log("WebSocket connection closed");
        };

        // Cleanup bei Unmount
        return () => {
            try {
                if (ws.readyState === WebSocket.OPEN) {
                    ws.close();
                }
            } catch (error) {
                console.error("Error closing WebSocket:", error);
            }
        };
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

export default StatusWebSocket;