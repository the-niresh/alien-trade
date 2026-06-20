/* eslint-disable */
/**
 * Generated `api` utility.
 *
 * THIS CODE IS AUTOMATICALLY GENERATED.
 *
 * To regenerate, run `npx convex dev`.
 * @module
 */

import type * as admin from "../admin.js";
import type * as agentCommands from "../agentCommands.js";
import type * as agentControl from "../agentControl.js";
import type * as agentEvents from "../agentEvents.js";
import type * as agentRuns from "../agentRuns.js";
import type * as approvals from "../approvals.js";
import type * as audit from "../audit.js";
import type * as config from "../config.js";
import type * as control from "../control.js";
import type * as copilot from "../copilot.js";
import type * as copilotNode from "../copilotNode.js";
import type * as decisions from "../decisions.js";
import type * as feedback from "../feedback.js";
import type * as forecastCalibration from "../forecastCalibration.js";
import type * as forecastState from "../forecastState.js";
import type * as ledger from "../ledger.js";
import type * as ping from "../ping.js";
import type * as positions from "../positions.js";
import type * as priceTicks from "../priceTicks.js";
import type * as push from "../push.js";
import type * as reflections from "../reflections.js";
import type * as riskState from "../riskState.js";
import type * as scorecard from "../scorecard.js";
import type * as signals from "../signals.js";
import type * as social from "../social.js";
import type * as spawnedAgents from "../spawnedAgents.js";
import type * as symbolList from "../symbolList.js";
import type * as thesisLedger from "../thesisLedger.js";
import type * as trades from "../trades.js";
import type * as twak from "../twak.js";
import type * as walletState from "../walletState.js";

import type {
  ApiFromModules,
  FilterApi,
  FunctionReference,
} from "convex/server";

declare const fullApi: ApiFromModules<{
  admin: typeof admin;
  agentCommands: typeof agentCommands;
  agentControl: typeof agentControl;
  agentEvents: typeof agentEvents;
  agentRuns: typeof agentRuns;
  approvals: typeof approvals;
  audit: typeof audit;
  config: typeof config;
  control: typeof control;
  copilot: typeof copilot;
  copilotNode: typeof copilotNode;
  decisions: typeof decisions;
  feedback: typeof feedback;
  forecastCalibration: typeof forecastCalibration;
  forecastState: typeof forecastState;
  ledger: typeof ledger;
  ping: typeof ping;
  positions: typeof positions;
  priceTicks: typeof priceTicks;
  push: typeof push;
  reflections: typeof reflections;
  riskState: typeof riskState;
  scorecard: typeof scorecard;
  signals: typeof signals;
  social: typeof social;
  spawnedAgents: typeof spawnedAgents;
  symbolList: typeof symbolList;
  thesisLedger: typeof thesisLedger;
  trades: typeof trades;
  twak: typeof twak;
  walletState: typeof walletState;
}>;

/**
 * A utility for referencing Convex functions in your app's public API.
 *
 * Usage:
 * ```js
 * const myFunctionReference = api.myModule.myFunction;
 * ```
 */
export declare const api: FilterApi<
  typeof fullApi,
  FunctionReference<any, "public">
>;

/**
 * A utility for referencing Convex functions in your app's internal API.
 *
 * Usage:
 * ```js
 * const myFunctionReference = internal.myModule.myFunction;
 * ```
 */
export declare const internal: FilterApi<
  typeof fullApi,
  FunctionReference<any, "internal">
>;

export declare const components: {};
