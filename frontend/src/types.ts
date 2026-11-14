export interface PlateInfo {
  id: string;
  name: string;
  object_ids: string[];
}

export interface ObjectMetrics {
  total_area_mm2: number;
  flat_top_area_mm2: number;
  domed_top_area_mm2: number;
  domed_ratio: number;
  cylindrical_score: number;
  steep_overhang_area_mm2: number;
  bridge_area_mm2: number;
  paint_enforcers_total: number;
  paint_blockers_total: number;
  base_enforcers_z8: number;
  base_blockers_z8: number;
}

export interface ObjectTelemetry {
  id: string;
  name: string;
  model_file: string;
  archetypes: string[];
  morphology_flags: string[];
  size_mm: [number, number, number];
  world_pos: [number, number, number];
  transform?: number[];
  footprint_l1_mm: [number, number];
  footprint_l10_mm: [number, number];
  l1_vertex_count: number;
  triangle_count: number;
  metrics: ObjectMetrics;
  overrides: Record<string, string>;
  mesh_preview?: {
    vertices: number[];
    indices: number[];
    vertex_zones: number[];
    vertex_extruders?: number[];
    filament_colours?: string[];
  };
}

export interface TelemetryData {
  filename: string;
  path: string;
  source_format?: '3mf' | 'stl';
  file_size_mb: number;
  plates: PlateInfo[];
  objects: ObjectTelemetry[];
}

export interface DiagnosticCard {
  id: string;
  pillar: 'safety' | 'aesthetics';
  object_id: string;
  object_tag: string;
  archetype: string;
  title: string;
  desc: string;
  pill_text: string;
  action_type:
    | 'FLATTEN_BOTTOM'
    | 'REINFORCE_SUPPORTS'
    | 'OPTIMIZE_SCREW'
    | 'ROTATE_YAW'
    | 'ADAPTIVE_LAYER_DOME'
    | 'IRONING_FLAT_TOP'
    | 'SCARF_SEAM_CYLINDER'
    | 'FUZZY_SKIN'
    | 'ARACHNE_FINE_DETAIL'
    | 'BRIDGE_AND_NECK_COOLING'
    | 'SWITCH_BED_PLATE'
    | 'MATERIAL_ADVICE';
  param_value: number;
  approved: boolean;
}

export interface SettingDiffItem {
  key: string;
  label: string;
  scope_tag: string;
  object_id: string;
  category: 'aesthetics' | 'adhesion' | 'kinematics' | 'support';
  meaning: string;
  default_val: string;
  author_val: string;
  proposed_val: string;
  reason: string;
  approved: boolean;
}

export interface AuditReport {
  summary: string;
  safety_score_before: number;
  safety_score_after: number;
  aesthetics_score_before: number;
  aesthetics_score_after: number;
  diagnostic_cards: DiagnosticCard[];
  settings_diff: SettingDiffItem[];
}

export interface SampleFile {
  name: string;
  path: string;
  size_mb: string;
}

export interface AgentActivityLog {
  id: string;
  step: string;
  title: string;
  detail: string;
  elapsed_s: number;
}

export interface AgentEngineInfo {
  id: 'claude' | 'agy' | 'engine';
  name: string;
  binary: string;
  path: string | null;
  version: string | null;
  available: boolean;
  badge: string;
  description: string;
}

export interface AgentEnginesResponse {
  engines: AgentEngineInfo[];
  default_engine: 'claude' | 'agy' | 'engine';
  has_multiple_clis: boolean;
  available_count: number;
}

/** One AMS filament slot as written by the model's author, plus what LayerZero will retarget it to. */
export interface FilamentSlotInfo {
  index: number;
  preset: string;
  type: string;
  colour: string;
  family: 'PLA' | 'PLA_LITE' | 'PETG' | 'SUPPORT' | 'OTHER';
  role: 'model' | 'support';
  /** UI filament key ('PLA Lite' | 'PLA Basic' | 'PETG HF'), or null when the slot keeps the author's settings. */
  target_filament: string | null;
  target_preset: string | null;
}

/** Resin preset (Anycubic Water-Wash Resin 2.0 on the Photon Mono 4, M.Studio fork GĐ2).
 * Numbers are Anycubic's manufacturer-recommended values, NOT verified on the user's own
 * printer; `colour` is the user's own resin (Gray, 1kg). */
export interface ResinPreset {
  name: string;
  vendor: string;
  printer: string;
  colour: string;
  bottle_kg: number;
  layer_height_mm: number;
  normal_exposure_s: number;
  normal_exposure_range_s: string;
  first_layer_exposure_range_s: string;
  bottom_exposure_s: number;
  bottom_layers: number;
  light_off_delay_s: number;
  z_lift_distance_mm: number;
  z_lift_speed_mm_s: number;
  z_retract_speed_mm_s: number;
  anti_aliasing: number;
  recommended_temp_c: string;
  wash: string;
  wash_note: string;
  cure_note: string;
  provenance: string;
}

/** Resolved printer / filament / plate context returned by the backend for the loaded file. */
export interface MaterialContext {
  printer_preset: string;
  printer_label: string;
  printer_vendor: 'bbl' | 'snapmaker' | 'anycubic';
  kinematics: 'bedslinger' | 'corexy' | 'corexy_toolchanger' | 'resin_mlsa';
  nozzle: string;
  /** Independent toolheads (Snapmaker U1: 4); null for AMS printers feeding one nozzle. */
  max_tools: number | null;
  slicer: SlicerId;
  /** Vendor the author saved the file for; null for STL / PrusaSlicer files. */
  source_vendor: 'bbl' | 'snapmaker' | 'anycubic' | null;
  /** True when export rebuilds the project from the target printer's presets (e.g. Bambu file -> U1). */
  cross_vendor_retarget: boolean;
  enclosed: boolean;
  filament: string;
  filament_preset: string;
  family: 'PLA' | 'PLA_LITE' | 'PETG' | 'SUPPORT' | 'OTHER' | 'RESIN';
  bed_type: string;
  bed_label: string;
  slots: FilamentSlotInfo[];
  mixed_model_families: boolean;
  /** Resin printers only: the resin preset itself (see `ResinPreset`). */
  resin_preset?: ResinPreset;
}

export type SlicerId = 'bambu_studio' | 'snapmaker_orca' | 'chitubox' | 'photon_workshop' | 'lychee';

export interface PrinterOption {
  id: string;
  label: string;
  vendor: 'bbl' | 'snapmaker' | 'anycubic';
  vendor_label: string;
  /** 'fdm' for filament printers, 'resin' for the Photon Mono 4. For resin, `nozzle` holds
   * the default layer height (0.05mm) and the label renders it as such. */
  technology: 'fdm' | 'resin';
  nozzle: string;
  kinematics: string;
  enclosed: boolean;
  max_tools: number | null;
  slicer: SlicerId;
}

export interface SlicerInfo {
  label: string;
  download_url: string;
  installed: boolean;
}

export interface PresetOptions {
  printers: PrinterOption[];
  slicers: Record<SlicerId, SlicerInfo>;
  filaments: { id: string; label: string; family: string; presets: Record<string, string> }[];
  /** Resin printers + presets, separate from the FDM filaments (a resin is not a filament). */
  resin?: {
    printers: string[];
    build_volume_mm: number[];
    presets: Record<string, ResinPreset>;
  };
  default_printer: string;
  default_filament: string;
}
