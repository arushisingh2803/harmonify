import { Doughnut } from "react-chartjs-2";
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend
} from "chart.js";

ChartJS.register(ArcElement, Tooltip, Legend);

type AvgFeatures = {
  tempo: number;
  centroid: number;
  zcr: number;
  rms: number;
  mfcc: number[];
};

export default function AudioProfileChart({ avg }: { avg: AvgFeatures }) {
  if (!avg) return null;

  const normalized = {
    tempo: Math.min(avg.tempo / 200, 1),
    brightness: Math.min(avg.centroid / 5000, 1),
    energy: Math.min(avg.rms, 1),
    mood: Math.min(avg.zcr, 1)
  };

  const metrics = [
    { label: "Tempo (BPM)", value: normalized.tempo * 200, color: "rgba(163,124,217,0.7)" },
    { label: "Brightness", value: normalized.brightness * 100, color: "rgba(242,146,146,0.7)" },
    { label: "Energy", value: normalized.energy * 100, color: "rgba(245,188,135,0.7)" },
    { label: "Mood", value: normalized.mood * 100, color: "rgba(128,205,185,0.7)" }
  ];

  return (
    <div className="chart-wrapper" style={{ display: "flex", flexDirection: "column", gap: "2rem", padding: "1rem" }}>  
      <div style={{ display: "flex", gap: "2rem", flexWrap: "wrap" }}>
        {metrics.map((metric, idx) => {
          const data = {
            labels: [metric.label, ""],
            datasets: [
              {
                data: [metric.value, 100 - metric.value],
                backgroundColor: [metric.color, "rgba(0,0,0,0.05)"],
                borderWidth: 0
              }
            ]
          };
          const options: any = {
            cutout: "70%",
            plugins: {
              legend: { display: false },
              tooltip: {
                callbacks: {
                  label: (context: any) => {
                    return `${metric.label}: ${metric.value.toFixed(0)}${metric.label === "Tempo (BPM)" ? " BPM" : "%"}`;
                  }
                }
              }
            }
          };
          return (
            <div key={idx} style={{ width: "120px", textAlign: "center" }}>
              <Doughnut data={data} options={options} />
              <p style={{ marginTop: "0.5rem", fontSize: "0.9rem", color: "#2b2b2b", fontWeight: 600 }}>{metric.label}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}