import "./index.css";
import React from "react";
import { Composition } from "remotion";
import { AdaptiveAIRouterVideo, TOTAL_DURATION } from "./Composition";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="AdaptiveAIRouterDemo"
        component={AdaptiveAIRouterVideo}
        durationInFrames={TOTAL_DURATION}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
