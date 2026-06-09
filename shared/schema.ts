import { z } from "zod";

// ── Nested types ──────────────────────────────────────────────────────────────

export const managedPropertySchema = z.object({
  propertyName:       z.string().min(1, "Property name required"),
  /** Total management pack % charged to the property owner */
  managementPackRate: z.coerce.number().min(0).max(100).optional(),
  /** Villa manager's personal cut from that management pack */
  commissionRate:     z.coerce.number().min(0).max(100),
});

export const b2bPropertySchema = z.object({
  propertyName:       z.string().min(1, "Property name required"),
  /** Total management pack % charged to the property owner */
  managementPackRate: z.coerce.number().min(0).max(100).optional(),
  /** Collaborator's commission cut */
  commissionRate:     z.coerce.number().min(0).max(100),
});

// ── Employee schema ───────────────────────────────────────────────────────────

export const employeeSchema = z.object({
  fullName:           z.string().min(2, "Full name required"),
  nickname:           z.string().optional(),
  dateOfBirth:        z.string().optional(),
  nationality:        z.string().min(2, "Nationality required"),
  idPassport:         z.string().min(3, "ID / Passport required"),
  address:            z.string().min(5, "Address required"),
  phone:              z.string().min(6, "Phone required"),
  position:           z.string().min(2, "Position required"),
  /** Additional roles / scope titles e.g. ["Concierge Provider", "Chef Service"] */
  additionalRoles:    z.array(z.string()).optional(),
  salary:             z.coerce.number().min(1, "Salary required"),
  startDate:          z.string().min(1, "Start date required"),
  /** For managers/revenue roles: list of properties they oversee + commission */
  managedProperties:  z.array(managedPropertySchema).optional(),
  /** Bonus system amounts */
  bonusPoolAmount:    z.coerce.number().optional(),  // THB per 6-month period
  eomRewardAmount:    z.coerce.number().optional(),  // Employee of month reward
  penaltyCapAmount:   z.coerce.number().optional(),  // Max penalty per event
});

// ── Collaborator schema (B2B) ─────────────────────────────────────────────────

export const collaboratorSchema = z.object({
  fullName:            z.string().min(2, "Full name required"),
  nickname:            z.string().optional(),
  dateOfBirth:         z.string().optional(),
  /** Does this collaborator represent a registered company? */
  isCompany:           z.boolean().optional(),
  companyName:         z.string().optional(),
  companyRegistration: z.string().optional(),
  companyTaxId:        z.string().optional(),
  companyAddress:      z.string().optional(),
  /** Representative / personal ID */
  idPassport:          z.string().min(3, "ID / Passport required"),
  phone:               z.string().min(6, "Phone required"),
  email:               z.string().email("Valid email required"),
  roles:               z.array(z.string()).optional(),  // one or more roles/positions
  services:            z.string().min(5, "Services description required"),
  /** Property-specific commission rates */
  properties:          z.array(b2bPropertySchema).optional(),
  /** Fallback general rate (used if no per-property rates are set) */
  commissionRate:      z.coerce.number().min(0).max(100).optional(),
  paymentTerms:        z.string().min(2, "Payment terms required"),
});

// ── Add-ons schema ────────────────────────────────────────────────────────────

export const addonsSchema = z.object({
  duties:              z.array(z.string()).default([]),
  complicatedFunctions:z.array(z.string()).default([]),
});

// ── Top-level contract form ───────────────────────────────────────────────────

export const contractFormSchema = z.object({
  contractType: z.enum(["employment", "b2b"]),
  department:   z.enum(["housekeeping", "office", "pool_garden_handyman"]).optional(),
  languages:    z.array(z.enum(["en", "th", "my"])).min(1, "Select at least one language"),
  employee:     employeeSchema.optional(),
  collaborator: collaboratorSchema.optional(),
  addons:       addonsSchema.default({ duties: [], complicatedFunctions: [] }),
});

// ── Exported types ────────────────────────────────────────────────────────────

export type ContractFormData   = z.infer<typeof contractFormSchema>;
export type EmployeeData       = z.infer<typeof employeeSchema>;
export type CollaboratorData   = z.infer<typeof collaboratorSchema>;
export type AddonsData         = z.infer<typeof addonsSchema>;
export type ManagedProperty    = z.infer<typeof managedPropertySchema>;
export type B2BProperty        = z.infer<typeof b2bPropertySchema>;
