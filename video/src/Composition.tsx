import React from "react";
import {
  Audio,
  Img,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export const SCENES = [
  {
    id: "scene1_intro",
    title: "The AI Infrastructure Dilemma",
    subtitle: "70%+ Queries Misrouted to Costly Frontier LLMs",
    audio: "assets/audio/scene1_intro.mp3",
    image: "assets/slide_1.png",
    durationInFrames: 520,
    caption:
      "Welcome to Adaptive AI Model Router. Over 70% of enterprise queries are simple factual requests, yet get blasted to expensive frontier models, causing massive latency and burning GPU budgets.",
  },
  {
    id: "scene2_solution",
    title: "Multi-Objective LLM Routing",
    subtitle: "Speed Mode (300ms) • Cost Mode (-80%) • Quality Mode",
    audio: "assets/audio/scene2_solution.mp3",
    image: "assets/slide_matrix.png",
    durationInFrames: 471,
    caption:
      "Our solution is an intelligent routing gateway: Speed Mode for sub-300ms LPU responses, Cost Mode for up to 80% token savings, or Quality Mode for deep frontier reasoning.",
  },
  {
    id: "scene3_architecture",
    title: "LangGraph Execution Engine",
    subtitle: "Stateful Graph + 99% Conf. Classifier + Qdrant Memory",
    audio: "assets/audio/scene3_architecture.mp3",
    image: "assets/slide_flow.png",
    durationInFrames: 399,
    caption:
      "Under the hood, a FastAPI service powers a stateful LangGraph DAG. Queries are classified with 99% accuracy, then evaluated against our in-memory Qdrant vector similarity cache.",
  },
  {
    id: "scene4_demo",
    title: "Live Demo & Semantic Caching",
    subtitle: "11.2x Latency Acceleration: 14,281ms ➔ 1,267ms",
    audio: "assets/audio/scene4_demo.mp3",
    image: "assets/dashboard_full.png",
    durationInFrames: 481,
    caption:
      "Here is our live running Streamlit dashboard. Semantic caching in Qdrant achieved an 11.2x speedup: cutting latency from 14.2s to 1.2s, with zero external model calls on cache hits.",
  },
  {
    id: "scene5_conclusion",
    title: "Production Resilience & Telemetry",
    subtitle: "PostgreSQL Audit Ledger • Graceful Degradation • Hackathon Ready",
    audio: "assets/audio/scene5_conclusion.mp3",
    image: "assets/slide_arch.png",
    durationInFrames: 341,
    caption:
      "Every decision is committed to an asynchronous PostgreSQL audit ledger. With instant heuristic fallbacks and silent degradation, Adaptive AI Model Router is production-ready.",
  },
];

export const TOTAL_DURATION = SCENES.reduce((acc, s) => acc + s.durationInFrames, 0);

export const AdaptiveAIRouterVideo: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  // Global Progress
  const progressPercent = (frame / TOTAL_DURATION) * 100;

  return (
    <div
      style={{
        flex: 1,
        backgroundColor: "#060913",
        color: "#f8fafc",
        fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        position: "relative",
        width,
        height,
        overflow: "hidden",
      }}
    >
      {/* Background Cyber Grid */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundImage:
            "linear-gradient(to right, rgba(0, 240, 255, 0.05) 1px, transparent 1px), linear-gradient(to bottom, rgba(0, 240, 255, 0.05) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
          pointerEvents: "none",
        }}
      />

      {/* Top Header Banner */}
      <div
        style={{
          position: "absolute",
          top: 30,
          left: 50,
          right: 50,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          zIndex: 100,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div
            style={{
              width: 14,
              height: 14,
              borderRadius: "50%",
              backgroundColor: "#00f0ff",
              boxShadow: "0 0 14px #00f0ff",
            }}
          />
          <span
            style={{
              fontSize: 22,
              fontWeight: 800,
              letterSpacing: "0.08em",
              color: "#ffffff",
              textTransform: "uppercase",
            }}
          >
            Adaptive AI Model Router
          </span>
          <span
            style={{
              fontSize: 13,
              backgroundColor: "rgba(0, 240, 255, 0.12)",
              border: "1px solid rgba(0, 240, 255, 0.4)",
              color: "#00f0ff",
              padding: "3px 10px",
              borderRadius: 20,
              fontWeight: 600,
              fontFamily: "monospace",
            }}
          >
            AI INFRA SUMMIT 2026
          </span>
        </div>

        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <span
            style={{
              fontSize: 13,
              color: "#94a3b8",
              fontFamily: "monospace",
              background: "rgba(255, 255, 255, 0.06)",
              padding: "4px 12px",
              borderRadius: 6,
              border: "1px solid rgba(255, 255, 255, 0.1)",
            }}
          >
            FASTAPI • LANGGRAPH • GROQ • QDRANT • POSTGRESQL
          </span>
        </div>
      </div>

      {/* Render Scenes in Sequences */}
      {SCENES.map((scene, index) => {
        const startFrame = SCENES.slice(0, index).reduce(
          (acc, s) => acc + s.durationInFrames,
          0
        );

        return (
          <Sequence
            key={scene.id}
            from={startFrame}
            durationInFrames={scene.durationInFrames}
          >
            <SceneContent scene={scene} index={index} />
            <Audio src={staticFile(scene.audio)} volume={1.0} />
          </Sequence>
        );
      })}

      {/* Bottom Global Progress Bar */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          width: "100%",
          height: 6,
          backgroundColor: "rgba(255, 255, 255, 0.08)",
          zIndex: 100,
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${progressPercent}%`,
            background: "linear-gradient(90deg, #a855f7, #00f0ff)",
            boxShadow: "0 0 12px #00f0ff",
          }}
        />
      </div>
    </div>
  );
};

const SceneContent: React.FC<{
  scene: (typeof SCENES)[0];
  index: number;
}> = ({ scene, index }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  // Smooth entrance spring
  const scale = spring({
    frame,
    fps,
    config: { damping: 18, stiffness: 85 },
  });

  const fadeIn = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Ken Burns subtle zoom
  const imageZoom = interpolate(
    frame,
    [0, scene.durationInFrames],
    [1.0, 1.05],
    {
      extrapolateRight: "clamp",
    }
  );

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width,
        height,
        opacity: fadeIn,
        display: "flex",
        flexDirection: "column",
        padding: "90px 50px 40px 50px",
        boxSizing: "border-box",
      }}
    >
      {/* Scene Header */}
      <div
        style={{
          marginBottom: 16,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-end",
        }}
      >
        <div>
          <div
            style={{
              fontSize: 13,
              color: "#00f0ff",
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.1em",
              marginBottom: 4,
              fontFamily: "monospace",
            }}
          >
            PART 0{index + 1} OF 05
          </div>
          <h1
            style={{
              fontSize: 34,
              fontWeight: 800,
              margin: 0,
              color: "#ffffff",
              letterSpacing: "-0.01em",
            }}
          >
            {scene.title}
          </h1>
          <div
            style={{
              fontSize: 18,
              color: "#a855f7",
              fontWeight: 600,
              marginTop: 4,
            }}
          >
            {scene.subtitle}
          </div>
        </div>

        <div
          style={{
            backgroundColor: "rgba(14, 22, 41, 0.85)",
            border: "1px solid rgba(0, 240, 255, 0.25)",
            borderRadius: 8,
            padding: "8px 16px",
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              backgroundColor: "#10b981",
              boxShadow: "0 0 8px #10b981",
            }}
          />
          <span style={{ fontSize: 13, color: "#94a3b8", fontFamily: "monospace" }}>
            LIVE DEMO VERIFIED
          </span>
        </div>
      </div>

      {/* Main Visual Display Frame */}
      <div
        style={{
          flex: 1,
          position: "relative",
          borderRadius: 14,
          overflow: "hidden",
          border: "2px solid rgba(0, 240, 255, 0.2)",
          backgroundColor: "rgba(10, 16, 32, 0.9)",
          boxShadow: "0 20px 50px rgba(0, 0, 0, 0.6)",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <Img
          src={staticFile(scene.image)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "contain",
            transform: `scale(${imageZoom})`,
            transition: "transform 0.1s ease-out",
          }}
        />

        {/* Cyber corner accents */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: 25,
            height: 25,
            borderTop: "3px solid #00f0ff",
            borderLeft: "3px solid #00f0ff",
          }}
        />
        <div
          style={{
            position: "absolute",
            top: 0,
            right: 0,
            width: 25,
            height: 25,
            borderTop: "3px solid #00f0ff",
            borderRight: "3px solid #00f0ff",
          }}
        />
        <div
          style={{
            position: "absolute",
            bottom: 0,
            left: 0,
            width: 25,
            height: 25,
            borderBottom: "3px solid #00f0ff",
            borderLeft: "3px solid #00f0ff",
          }}
        />
        <div
          style={{
            position: "absolute",
            bottom: 0,
            right: 0,
            width: 25,
            height: 25,
            borderBottom: "3px solid #00f0ff",
            borderRight: "3px solid #00f0ff",
          }}
        />
      </div>

      {/* Dynamic Subtitle / Narration Lower-Third */}
      <div
        style={{
          marginTop: 14,
          backgroundColor: "rgba(14, 22, 41, 0.9)",
          border: "1px solid rgba(168, 85, 247, 0.3)",
          borderRadius: 10,
          padding: "12px 24px",
          display: "flex",
          alignItems: "center",
          gap: 16,
          backdropFilter: "blur(8px)",
          boxShadow: "0 4px 20px rgba(0,0,0,0.4)",
        }}
      >
        <div
          style={{
            fontSize: 20,
            color: "#00f0ff",
          }}
        >
          🎙️
        </div>
        <p
          style={{
            margin: 0,
            fontSize: 16,
            lineHeight: 1.45,
            color: "#e2e8f0",
            fontWeight: 500,
          }}
        >
          {scene.caption}
        </p>
      </div>
    </div>
  );
};
