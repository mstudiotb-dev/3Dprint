import React from 'react';
import { PrinterOption } from '../types';

/** Printers shown before the backend answers `/api/presets` (ids must match backend `PRINTERS`). */
export const FALLBACK_PRINTERS: PrinterOption[] = [
  ...[
    ['Bambu Lab A1 0.4 nozzle', 'A1', 'bedslinger', false],
    ['Bambu Lab A1 mini 0.4 nozzle', 'A1 mini', 'bedslinger', false],
    ['Bambu Lab P1S 0.4 nozzle', 'P1S', 'corexy', true],
    ['Bambu Lab X1 Carbon 0.4 nozzle', 'X1C', 'corexy', true],
  ].map(([id, label, kinematics, enclosed]) => ({
    id: id as string,
    label: label as string,
    vendor: 'bbl' as const,
    vendor_label: 'Bambu Lab',
    technology: 'fdm' as const,
    nozzle: '0.4',
    kinematics: kinematics as string,
    enclosed: enclosed as boolean,
    max_tools: null,
    slicer: 'bambu_studio' as const,
  })),
  ...['0.2', '0.4', '0.6', '0.8'].map((nozzle) => ({
    id: `Snapmaker U1 (${nozzle} nozzle)`,
    label: 'U1',
    vendor: 'snapmaker' as const,
    vendor_label: 'Snapmaker',
    technology: 'fdm' as const,
    nozzle,
    kinematics: 'corexy_toolchanger',
    enclosed: false,
    max_tools: 4,
    slicer: 'snapmaker_orca' as const,
  })),
  // M.Studio fork, GĐ2: Anycubic Photon Mono 4 (resin, MSLA). `nozzle` holds the default
  // layer height (0.05mm) — resin has no nozzle. The user slices with CHITUBOX.
  {
    id: 'Anycubic Photon Mono 4',
    label: 'Photon Mono 4',
    vendor: 'anycubic' as const,
    vendor_label: 'Anycubic',
    technology: 'resin' as const,
    nozzle: '0.05',
    kinematics: 'resin_mlsa',
    enclosed: false,
    max_tools: null,
    slicer: 'chitubox' as const,
  },
];

/** FDM: "A1 (0.4mm)"; resin: "Photon Mono 4 (resin · layer 0.05mm)". */
export const printerOptionLabel = (p: PrinterOption) =>
  p.technology === 'resin' ? `${p.label} (resin · layer ${p.nozzle}mm)` : `${p.label} (${p.nozzle}mm)`;

interface PrinterSelectProps {
  printers: PrinterOption[];
  value: string;
  onChange: (printerId: string) => void;
  className?: string;
  /** Extra first option (e.g. "same as selected printer"), rendered with an empty value. */
  leadingOption?: string;
  title?: string;
}

/** Printer dropdown grouped by vendor (Bambu Lab / Snapmaker / Anycubic resin),
 * each entry showing its nozzle size (resin: layer height). */
export const PrinterSelect: React.FC<PrinterSelectProps> = ({ printers, value, onChange, className, leadingOption, title }) => {
  const vendors = Array.from(new Set(printers.map((p) => p.vendor_label)));
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)} className={className} title={title}>
      {leadingOption !== undefined && <option value="">{leadingOption}</option>}
      {vendors.map((vendor) => (
        <optgroup key={vendor} label={vendor}>
          {printers
            .filter((p) => p.vendor_label === vendor)
            .map((p) => (
              <option key={p.id} value={p.id}>
                {printerOptionLabel(p)}
              </option>
            ))}
        </optgroup>
      ))}
    </select>
  );
};
