import { create } from 'zustand';

export interface Reel {
  id: string;
  title: string;
  caption: string;
  transcript_excerpt: string;
  creator_handle: string;
  duration_sec: number;
  tags: string[];
  thumbnail_gradient: string[];
  engagement?: {
    watch_completion: number;
    rewatched: boolean;
    liked: boolean;
    saved: boolean;
    shared: boolean;
    commented: boolean;
    skipped_at_sec: number | null;
  };
}

export interface InterestNode {
  id: string;
  label: string;
  layer: 'L1' | 'L2' | 'L3';
  convergence: number;
  supporting_reels: string[];
  weight: number;
}

export interface InterestEdge {
  source: string;
  target: string;
  weight: number;
}

export interface SubstancePenalty {
  name: string;
  score_delta: number;
  triggered_by: string;
  flagged_phrase: string | null;
}

export interface SubstanceReport {
  candidate_id: string;
  title: string;
  raw_score: number;
  penalties: SubstancePenalty[];
  final_score: number;
  passed: boolean;
  rejection_reason: string | null;
  transcript_excerpt: string | null;
}

export interface Recommendation {
  rec_id: string;
  candidate_id: string;
  title: string;
  category: string;
  difficulty: string;
  confidence: 'High' | 'Medium' | 'Low';
  interest_detected: string;
  why_evidence: string;
  why_recommendation: string;
  formatted_block: string;
  is_serendipity: boolean;
  serendipity_label: string | null;
  creator_handle: string;
  hook_style: string;
  substance_score: number;
  zero_signal_note?: string;
}

export interface AgentStage {
  stage: number;
  label: string;
  status: 'pending' | 'running' | 'done';
  data?: unknown;
}

export type Mode = 'agent' | 'shallow';

interface SignalState {
  // Session
  sessionId: string | null;
  setSessionId: (id: string) => void;

  // Mode
  mode: Mode;
  setMode: (mode: Mode) => void;

  // Reels
  reels: Reel[];
  setReels: (reels: Reel[]) => void;
  currentReelIdx: number;
  setCurrentReelIdx: (idx: number) => void;

  // Interactions
  interactions: Record<string, { liked: boolean; saved: boolean; shared: boolean }>;
  setInteraction: (reelId: string, key: 'liked' | 'saved' | 'shared', val: boolean) => void;

  // Agent pipeline state
  stages: AgentStage[];
  updateStage: (stage: number, status: 'running' | 'done', data?: unknown) => void;
  resetStages: () => void;

  // Graph
  graphNodes: InterestNode[];
  graphEdges: InterestEdge[];
  latentNeed: string;
  topL3: InterestNode | null;
  topL2: InterestNode[];
  shallowMovesBlocked: string[];
  setGraph: (nodes: InterestNode[], edges: InterestEdge[], latentNeed: string, topL3: InterestNode | null, topL2: InterestNode[]) => void;

  // Substance
  rejectedCandidates: SubstanceReport[];
  passedCount: number;
  setSubstance: (rejected: SubstanceReport[], passedCount: number) => void;

  // Recommendation
  recommendation: Recommendation | null;
  alternates: Recommendation[];
  serendipity: Recommendation | null;
  confidence: string;
  confidenceReason: string;
  setRecommendation: (rec: Recommendation | null, alts: Recommendation[], seren: Recommendation | null, conf: string, reason: string) => void;

  // Stream state
  isStreaming: boolean;
  setIsStreaming: (v: boolean) => void;
  streamLog: string[];
  addStreamLog: (msg: string) => void;
  clearStreamLog: () => void;

  // Offline mode
  isOffline: boolean;
  setIsOffline: (v: boolean) => void;

  // Server Error State (Part 2.2)
  serverError: string | null;
  setServerError: (msg: string | null) => void;

  fullTrace: unknown;
  setFullTrace: (trace: unknown) => void;
}

const INITIAL_STAGES: AgentStage[] = [
  { stage: 1, label: 'Semantic Decomposition', status: 'pending' },
  { stage: 2, label: 'Interest Graph Synthesis', status: 'pending' },
  { stage: 3, label: 'Candidate Retrieval', status: 'pending' },
  { stage: 4, label: 'Substance Gate', status: 'pending' },
  { stage: 5, label: 'Fit Ranking', status: 'pending' },
  { stage: 6, label: 'Confidence Calibration', status: 'pending' },
  { stage: 7, label: 'Explanation & Recommendation', status: 'pending' },
];

export const useStore = create<SignalState>((set) => ({
  sessionId: null,
  setSessionId: (id) => set({ sessionId: id }),

  mode: 'agent',
  setMode: (mode) => set({ mode }),

  reels: [],
  setReels: (reels) => set({ reels }),
  currentReelIdx: 0,
  setCurrentReelIdx: (idx) => set({ currentReelIdx: idx }),

  interactions: {},
  setInteraction: (reelId, key, val) =>
    set((s) => ({
      interactions: {
        ...s.interactions,
        [reelId]: { ...(s.interactions[reelId] || { liked: false, saved: false, shared: false }), [key]: val },
      },
    })),

  stages: INITIAL_STAGES,
  updateStage: (stage, status, data) =>
    set((s) => ({
      stages: s.stages.map((st) => (st.stage === stage ? { ...st, status, data } : st)),
    })),
  resetStages: () => set({ stages: INITIAL_STAGES.map((s) => ({ ...s, status: 'pending' })) }),

  graphNodes: [],
  graphEdges: [],
  latentNeed: '',
  topL3: null,
  topL2: [],
  shallowMovesBlocked: [],
  setGraph: (nodes, edges, latentNeed, topL3, topL2) =>
    set({ graphNodes: nodes, graphEdges: edges, latentNeed, topL3, topL2 }),

  rejectedCandidates: [],
  passedCount: 0,
  setSubstance: (rejected, passedCount) => set({ rejectedCandidates: rejected, passedCount }),

  recommendation: null,
  alternates: [],
  serendipity: null,
  confidence: '',
  confidenceReason: '',
  setRecommendation: (rec, alts, seren, conf, reason) =>
    set({ recommendation: rec, alternates: alts, serendipity: seren, confidence: conf, confidenceReason: reason }),

  isStreaming: false,
  setIsStreaming: (v) => set({ isStreaming: v }),
  streamLog: [],
  addStreamLog: (msg) => set((s) => ({ streamLog: [...s.streamLog.slice(-50), msg] })),
  clearStreamLog: () => set({ streamLog: [] }),

  isOffline: false,
  setIsOffline: (v) => set({ isOffline: v }),

  serverError: null,
  setServerError: (msg) => set({ serverError: msg }),

  fullTrace: null,
  setFullTrace: (trace) => set({ fullTrace: trace }),
}));
