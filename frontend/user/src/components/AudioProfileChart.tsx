import React from "react";
import { Radar, Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  RadialLinearScale,
  BarElement,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale
} from "chart.js";

ChartJS.register(
  RadialLinearScale,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend
);

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
    tempo: avg.tempo / 200,
    brightness: avg.centroid / 5000,
    noisiness: avg.zcr,
    energy: avg.rms, 
  };

  const radarData = {
    labels: ["Tempo", "Brightness", "Noisiness", "Energy"],
    datasets: [
      {
        label: "Your Average Audio Profile",
        data: [
          normalized.tempo,
          normalized.brightness,
          normalized.noisiness,
          normalized.energy,
        ],
        backgroundColor: "rgba(75, 192, 192, 0.4)",
        borderColor: "rgba(75, 192, 192, 1)",
        borderWidth: 2,
      },
    ],
  };

  const radarOptions: any = {
    scales: {
      r: {
        suggestedMin: 0,
        suggestedMax: 1,
        ticks: { stepSize: 0.2 },
      },
    },
  };

  const mfccData = {
    labels: avg.mfcc.map((_, i) => `MFCC ${i + 1}`),
    datasets: [
      {
        label: "MFCC Coefficients",
        data: avg.mfcc,
        backgroundColor: "rgba(153, 102, 255, 0.6)",
      },
    ],
  };

  return (
    <div style={{ marginTop: "2rem" }}>
      <h2>🎧 Your Audio Profile (Aggregated)</h2>

      <div style={{ width: "500px", marginBottom: "3rem" }}>
        <h3>Overall Timbre & Brightness Profile</h3>
        <Radar data={radarData} options={radarOptions} />
      </div>

      <div style={{ width: "700px" }}>
        <h3>MFCC Timbre Fingerprint</h3>
        <Bar data={mfccData} />
      </div>
    </div>
  );
}
