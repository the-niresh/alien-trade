/* eslint-disable */
/**
 * Generated `api` utility.
 *
 * THIS CODE IS AUTOMATICALLY GENERATED.
 *
 * To regenerate, run `npx convex dev`.
 * @module
 */

import type * as agentControl from "../agentControl.js";
import type * as agentEvents from "../agentEvents.js";
import type * as audit from "../audit.js";
import type * as config from "../config.js";
import type * as control from "../control.js";
import type * as copilot from "../copilot.js";
import type * as decisions from "../decisions.js";
import type * as feedback from "../feedback.js";
import type * as forecastCalibration from "../forecastCalibration.js";
import type * as forecastState from "../forecastState.js";
import type * as ledger from "../ledger.js";
import type * as reflections from "../reflections.js";
import type * as riskState from "../riskState.js";
import type * as scorecard from "../scorecard.js";
import type * as social from "../social.js";
import type * as thesisLedger from "../thesisLedger.js";
import type * as trades from "../trades.js";

import type {
  ApiFromModules,
  FilterApi,
  FunctionReference,
} from "convex/server";

declare const fullApi: ApiFromModules<{
  agentControl: typeof agentControl;
  agentEvents: typeof agentEvents;
  audit: typeof audit;
  config: typeof config;
  control: typeof control;
  copilot: typeof copilot;
  decisions: typeof decisions;
  feedback: typeof feedback;
  forecastCalibration: typeof forecastCalibration;
  forecastState: typeof forecastState;
  ledger: typeof ledger;
  reflections: typeof reflections;
  riskState: typeof riskState;
  scorecard: typeof scorecard;
  social: typeof social;
  thesisLedger: typeof thesisLedger;
  trades: typeof trades;
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
