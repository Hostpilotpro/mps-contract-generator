import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import { employeeSchema, collaboratorSchema } from "@shared/schema";
import type { EmployeeData, CollaboratorData, ManagedProperty, B2BProperty } from "@shared/schema";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Form, FormField, FormItem, FormControl, FormMessage,
} from "@/components/ui/form";
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "@/components/ui/select";
import {
  Briefcase, Users, Home, Building2, Wrench, Download, CheckCircle2,
  ChevronRight, ChevronLeft, FileText, Languages, Loader2, Plus, Trash2,
  Building, User,
} from "lucide-react";

// ─── DUTY DATA ────────────────────────────────────────────────────────────────

const DUTY_LABELS: Record<string, { en: string; th: string; my: string }> = {
  welcome_setup:       { en: "Welcome setup & villa preparation",            th: "การเตรียมวิลล่าต้อนรับแขก",              my: "ဧည့်သည်ကြိုဆိုရေး ပြင်ဆင်မှု" },
  villa_inspection:    { en: "Villa inspection & quality checks",             th: "การตรวจสอบวิลล่าและควบคุมคุณภาพ",         my: "ဗိလာ စစ်ဆေးမှုနှင့် အရည်အသွေး" },
  guest_laundry:       { en: "Guest laundry service",                         th: "บริการซักรีดสำหรับแขก",                   my: "ဧည့်သည် အဝတ်လျော်ဝန်ဆောင်မှု" },
  ironing:             { en: "Ironing & garment care",                        th: "รีดเสื้อผ้าและดูแลเครื่องแต่งกาย",       my: "အဝတ်ချောင်းဖွာနှင့် အဝတ်အစားပြုစု" },
  inventory_mgmt:      { en: "Inventory management & restocking",             th: "การจัดการสต็อกสินค้าและเติม",            my: "ပစ္စည်းစာရင်းနှင့် အဖြည့်" },
  train_staff:         { en: "Training new housekeeping staff",               th: "ฝึกอบรมพนักงานแม่บ้านใหม่",             my: "မြိုတ်သစ်ဝန်ထမ်းများ သင်ကြားပေးမှု" },
  multi_property_hk:   { en: "Multi-property rotation (housekeeping)",        th: "หมุนเวียนหลายทรัพย์สิน",               my: "မြေပိုင်အများ ကွင်းဆင်းမှု" },
  night_checkout_clean:{ en: "Night / late check-out cleaning",              th: "ทำความสะอาดหลัง check-out ดึก",          my: "ည / နောက်ကျ check-out ဆဲဆေးမှု" },
  airport_transfer:    { en: "Airport transfer coordination",                 th: "ประสานรับส่งสนามบิน",                    my: "လေဆိပ်သယ်ပို့ ညှိနှိုင်းမှု" },
  concierge_booking:   { en: "Concierge & booking management",                th: "บริการ concierge และจัดการการจอง",       my: "Concierge နှင့် ကြိုတင်မှာကြားမှု" },
  checkin_checkout:    { en: "Check-in / check-out management",               th: "จัดการ check-in / check-out",            my: "Check-in / check-out စီမံမှု" },
  maintenance_sched:   { en: "Maintenance scheduling",                        th: "กำหนดตารางซ่อมบำรุง",                   my: "ပြုပြင်ထိန်းသိမ်းမှု ဇယားဆွဲ" },
  vendor_mgmt:         { en: "Vendor management",                             th: "จัดการผู้จัดจำหน่าย",                   my: "ကုန်ပစ္စည်းပေးသွင်းသူ စီမံ" },
  social_media:        { en: "Social media monitoring",                       th: "ติดตามสื่อสังคมออนไลน์",                my: "လူမှုကွန်ရက် ကြည့်ရှုခြင်း" },
  platform_mgmt:       { en: "Platform management (Airbnb / Booking.com)",    th: "จัดการแพลตฟอร์ม (Airbnb/Booking.com)", my: "Platform စီမံမှု (Airbnb/Booking.com)" },
  revenue_mgmt:        { en: "Revenue management & dynamic pricing",          th: "บริหารรายได้และกำหนดราคาไดนามิก",       my: "ဝင်ငွေစီမံမှုနှင့် ဈေးနှုန်းညှိ" },
  staff_scheduling:    { en: "Staff scheduling & rotas",                      th: "จัดตารางพนักงานและเวร",                 my: "ဝန်ထမ်းဇယားနှင့် တာဝန်ကြိမ်" },
  petty_cash_mgmt:     { en: "Petty cash management",                         th: "จัดการเงินสดย่อย",                      my: "ငွေသေးစိတ် စီမံမှု" },
  chemical_testing:    { en: "Chemical testing & water balance",              th: "ทดสอบสารเคมีและปรับสมดุลน้ำ",           my: "ဓာတုပစ္စည်း စစ်ဆေးမှုနှင့် ရေချိန်ညှိ" },
  equipment_maint:     { en: "Equipment maintenance (pumps, filters)",        th: "ซ่อมบำรุงอุปกรณ์ (ปั๊ม, ตัวกรอง)",     my: "ကိရိယာပြုပြင် (ပန့်၊ စစ်စစ်)" },
  jacuzzi_spa:         { en: "Jacuzzi / spa maintenance",                     th: "ดูแลแจ็คคูซี่และสปา",                  my: "Jacuzzi / spa ထိန်းသိမ်း" },
  lawn_landscaping:    { en: "Lawn mowing & landscaping",                     th: "ตัดหญ้าและจัดภูมิทัศน์",               my: "မြက်ခုတ်နှင့် ဥယျာဉ်ဒီဇိုင်း" },
  pest_control:        { en: "Pest control & prevention",                     th: "กำจัดและป้องกันแมลง",                   my: "ကောင်ပိုးပြောင်းဆေး" },
  minor_plumbing:      { en: "Minor plumbing repairs",                        th: "ซ่อมแซมระบบประปาเล็กน้อย",             my: "ရေပိုက်ပြုပြင်" },
  minor_electrical:    { en: "Minor electrical work",                         th: "งานไฟฟ้าเล็กน้อย",                      my: "လျှပ်စစ်လုပ်ငန်းငယ်" },
  ac_filter:           { en: "AC filter cleaning & maintenance",              th: "ทำความสะอาดและดูแล filter แอร์",        my: "အဲယားကွန်း filter သန့်ရှင်း" },
  painting:            { en: "Painting & touch-ups",                          th: "ทาสีและแก้ไขผิวงาน",                   my: "ဆေးသုတ်မှုနှင့် ပြင်ဆင်" },
  vehicle_cleaning:    { en: "Vehicle cleaning & upkeep",                     th: "ทำความสะอาดและดูแลยานพาหนะ",           my: "ယာဉ် သန့်ရှင်းနှင့် ထိန်းသိမ်း" },
  multi_property_pg:   { en: "Multi-property rotation",                       th: "หมุนเวียนหลายทรัพย์สิน",               my: "မြေပိုင်အများ ကွင်းဆင်းမှု" },
  emergency_oncall_pg: { en: "Emergency on-call duty",                        th: "เวรฉุกเฉิน (on-call)",                  my: "အရေးပေါ် on-call တာဝန်" },
  supervise_train_pg:  { en: "Supervise & train team members",               th: "ดูแลและฝึกอบรมสมาชิกทีม",              my: "အဖွဲ့ဝင်များ ကြီးကြပ်/သင်ကြားပေး" },
  night_shift_rotation:{ en: "Night shift rotation (adds night-work clause)", th: "กะกลางคืนหมุนเวียน (เพิ่มข้อการทำงานกลางคืน)", my: "ညဆိုင်းကြိမ်ကူး (ညအလုပ်ဘောင် ထည့်)" },
  on_call_avail:       { en: "On-call availability (outside normal hours)",   th: "พร้อมรับเวร (นอกเวลางานปกติ)",          my: "On-call ရနိုင်မှု (ပုံမှန်အချိန်ပြင်ပ)" },
  multi_property_cover:{ en: "Multi-property coverage",                       th: "ดูแลหลายทรัพย์สิน",                    my: "မြေပိုင်အများ ကာကွယ်မှု" },
  training_resp:       { en: "Training responsibility for other staff",       th: "รับผิดชอบฝึกอบรมพนักงานอื่น",           my: "အခြားဝန်ထမ်းများ သင်ကြားပေးရသော တာဝန်" },
  petty_cash_handling: { en: "Petty cash handling",                           th: "จัดการเงินสดย่อย",                      my: "ငွေသေးစိတ် ကိုင်တွယ်မှု" },
};

const DEPT_DUTIES: Record<string, string[]> = {
  housekeeping: ["welcome_setup","villa_inspection","guest_laundry","ironing","inventory_mgmt","train_staff","multi_property_hk","night_checkout_clean"],
  office: ["airport_transfer","concierge_booking","checkin_checkout","maintenance_sched","vendor_mgmt","social_media","platform_mgmt","revenue_mgmt","staff_scheduling","petty_cash_mgmt"],
  pool_garden_handyman: ["chemical_testing","equipment_maint","jacuzzi_spa","lawn_landscaping","pest_control","minor_plumbing","minor_electrical","ac_filter","painting","vehicle_cleaning","multi_property_pg","emergency_oncall_pg","supervise_train_pg"],
};
const COMPLICATED_KEYS = ["night_shift_rotation","on_call_avail","multi_property_cover","training_resp","petty_cash_handling"];

// ─── JOB TITLES ───────────────────────────────────────────────────────────────

const EMP_TITLES: Record<string, Array<{ value: string; label: string }>> = {
  housekeeping: [
    { value: "Villa Housekeeper",       label: "Villa Housekeeper" },
    { value: "Head Housekeeper",        label: "Head Housekeeper" },
    { value: "Housekeeping Supervisor", label: "Housekeeping Supervisor" },
    { value: "Laundry Attendant",       label: "Laundry Attendant" },
    { value: "Turn-down Attendant",     label: "Turn-down Attendant" },
    { value: "Cleaning Team Leader",    label: "Cleaning Team Leader" },
    { value: "__custom__",              label: "Custom title…" },
  ],
  office: [
    { value: "Villa Manager",              label: "Villa Manager" },
    { value: "Property Manager",           label: "Property Manager" },
    { value: "Operations Manager",         label: "Operations Manager" },
    { value: "Guest Relations Officer",    label: "Guest Relations Officer" },
    { value: "Reservations Coordinator",   label: "Reservations Coordinator" },
    { value: "Revenue & Platform Manager", label: "Revenue & Platform Manager" },
    { value: "Front Desk Officer",         label: "Front Desk Officer" },
    { value: "Admin & Accounts Officer",   label: "Admin & Accounts Officer" },
    { value: "__custom__",                 label: "Custom title…" },
  ],
  pool_garden_handyman: [
    { value: "Pool & Garden Technician",   label: "Pool & Garden Technician" },
    { value: "Handyman",                   label: "Handyman" },
    { value: "Maintenance Technician",     label: "Maintenance Technician" },
    { value: "Landscaping Specialist",     label: "Landscaping Specialist" },
    { value: "Pool Attendant",             label: "Pool Attendant" },
    { value: "Multi-Skill Technician",     label: "Multi-Skill Technician" },
    { value: "Head Maintenance Technician",label: "Head Maintenance Technician" },
    { value: "__custom__",                 label: "Custom title…" },
  ],
};

const B2B_TITLES: Array<{ value: string; label: string; group?: string }> = [
  // Management
  { value: "Property Management Company",     label: "Property Management Company",     group: "Management" },
  { value: "Villa Manager (B2B)",             label: "Villa Manager (B2B)",             group: "Management" },
  { value: "Revenue & Booking Manager",       label: "Revenue & Booking Manager",       group: "Management" },
  { value: "Property Consultant / Advisor",   label: "Property Consultant / Advisor",   group: "Management" },
  { value: "Guest Experience Manager",        label: "Guest Experience Manager",        group: "Management" },
  { value: "Key Account Manager",             label: "Key Account Manager",             group: "Management" },
  // Sales & Marketing
  { value: "Booking Agent / OTA Manager",     label: "Booking Agent / OTA Manager",     group: "Sales & Marketing" },
  { value: "Marketing & Social Media Partner",label: "Marketing & Social Media Partner",group: "Sales & Marketing" },
  { value: "Event Coordinator",               label: "Event Coordinator",               group: "Sales & Marketing" },
  { value: "Photography & Videography",       label: "Photography & Videography",       group: "Sales & Marketing" },
  // Operations & Maintenance
  { value: "Cleaning Service Provider",       label: "Cleaning Service Provider",       group: "Operations" },
  { value: "Maintenance & Handyman Contractor",label:"Maintenance & Handyman Contractor",group: "Operations" },
  { value: "Landscaping & Pool Service",      label: "Landscaping & Pool Service",      group: "Operations" },
  { value: "Airport Transfer Service",        label: "Airport Transfer Service",        group: "Operations" },
  { value: "Laundry & Linen Service",         label: "Laundry & Linen Service",        group: "Operations" },
  { value: "Chef / Catering Service",         label: "Chef / Catering Service",         group: "Operations" },
  { value: "Security Services",               label: "Security Services",               group: "Operations" },
  // Professional Services
  { value: "Accounting & Financial Services", label: "Accounting & Financial Services", group: "Professional" },
  { value: "Legal & Compliance Consultant",   label: "Legal & Compliance Consultant",   group: "Professional" },
  { value: "IT & Smart Home Services",        label: "IT & Smart Home Services",        group: "Professional" },
  { value: "Interior Design & Styling",       label: "Interior Design & Styling",       group: "Professional" },
  { value: "__custom__",                      label: "Custom / Other…" },
];

// ─── HELPER COMPONENTS ────────────────────────────────────────────────────────

function TriLabel({ en, th, my }: { en: string; th: string; my: string }) {
  return (
    <div className="tri-label">
      <span className="en">{en}</span>
      <span className="th">{th}</span>
      <span className="my">{my}</span>
    </div>
  );
}

function StepDot({ num, current }: { num: number; current: number }) {
  const s = num < current ? "done" : num === current ? "active" : "inactive";
  return <div className={`step-indicator ${s}`} data-testid={`step-dot-${num}`}>{num < current ? "✓" : num}</div>;
}

function StepBar({ step }: { step: number }) {
  const steps = [
    { label: "Setup" }, { label: "Details" }, { label: "Add-ons" }, { label: "Generate" },
  ];
  return (
    <div className="px-6 py-4 border-b" style={{ borderColor: "hsl(var(--border))" }}>
      <div className="flex items-start max-w-2xl mx-auto">
        {steps.map((s, i) => (
          <div key={i} className="flex items-start flex-1">
            <div className="flex flex-col items-center gap-1 min-w-0">
              <StepDot num={i + 1} current={step} />
              <div className="text-center hidden sm:block">
                <div className="text-xs font-semibold" style={{ color: step === i + 1 ? "var(--gold)" : "hsl(var(--muted-foreground))" }}>
                  {s.label}
                </div>
              </div>
            </div>
            {i < steps.length - 1 && (
              <div className="flex-1 h-0.5 mx-1 mt-4 transition-all duration-300"
                style={{ background: step > i + 1 ? "var(--gold)" : "hsl(var(--border))" }} />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function SectionHead({ children }: { children: React.ReactNode }) {
  return (
    <div className="mb-4">
      <h3 className="font-bold text-base" style={{ color: "var(--navy)", fontFamily: "'Playfair Display', Georgia, serif" }}>{children}</h3>
      <div className="section-divider" />
    </div>
  );
}

// ─── PROPERTY TABLE ───────────────────────────────────────────────────────────

function PropertyTable({
  rows,
  onAdd,
  onRemove,
  onUpdate,
  placeholder,
  label,
  rateLabel,
  packLabel,
}: {
  rows: Array<{ propertyName: string; managementPackRate?: number; commissionRate: number }>;
  onAdd: () => void;
  onRemove: (i: number) => void;
  onUpdate: (i: number, field: "propertyName" | "managementPackRate" | "commissionRate", value: string | number) => void;
  placeholder?: string;
  label?: string;
  rateLabel?: string;
  packLabel?: string;
}) {
  return (
    <div className="space-y-2">
      {rows.length === 0 ? (
        <p className="text-sm" style={{ color: "hsl(var(--muted-foreground))" }}>
          {placeholder ?? "No properties added yet. Click below to add."}
        </p>
      ) : (
        <div className="space-y-2">
          {/* Header */}
          <div className="grid grid-cols-[1fr_90px_90px_32px] gap-2 px-1">
            <span className="text-xs font-medium" style={{ color: "hsl(var(--muted-foreground))" }}>Property / Villa Name</span>
            <span className="text-xs font-medium" style={{ color: "hsl(var(--muted-foreground))" }}>{packLabel ?? "Mgmt Pack %"}</span>
            <span className="text-xs font-medium" style={{ color: "hsl(var(--muted-foreground))" }}>{rateLabel ?? "Cut of Pack %"}</span>
            <span />
          </div>
          {rows.map((row, i) => (
            <div key={i} className="grid grid-cols-[1fr_90px_90px_32px] gap-2 items-center" data-testid={`property-row-${i}`}>
              <Input
                placeholder="e.g. Villa Lotus"
                value={row.propertyName}
                onChange={(e) => onUpdate(i, "propertyName", e.target.value)}
                data-testid={`input-prop-name-${i}`}
              />
              <div className="relative">
                <Input
                  type="number"
                  min={0}
                  max={100}
                  placeholder="15"
                  value={(row.managementPackRate ?? 0) === 0 ? "" : row.managementPackRate}
                  onChange={(e) => onUpdate(i, "managementPackRate", e.target.value)}
                  data-testid={`input-prop-pack-${i}`}
                  className="pr-5"
                />
                <span className="absolute right-2 top-1/2 -translate-y-1/2 text-sm" style={{ color: "hsl(var(--muted-foreground))" }}>%</span>
              </div>
              <div className="relative">
                <Input
                  type="number"
                  min={0}
                  max={100}
                  placeholder="8"
                  value={row.commissionRate === 0 ? "" : row.commissionRate}
                  onChange={(e) => onUpdate(i, "commissionRate", e.target.value)}
                  data-testid={`input-prop-rate-${i}`}
                  className="pr-5"
                />
                <span className="absolute right-2 top-1/2 -translate-y-1/2 text-sm" style={{ color: "hsl(var(--muted-foreground))" }}>%</span>
              </div>
              <button
                type="button"
                onClick={() => onRemove(i)}
                className="flex items-center justify-center w-8 h-8 rounded-md transition-colors"
                style={{ color: "hsl(var(--destructive))" }}
                data-testid={`btn-remove-prop-${i}`}
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
      <Button type="button" variant="outline" size="sm" onClick={onAdd} data-testid="btn-add-property">
        <Plus className="w-3.5 h-3.5 mr-1" /> Add {label ?? "Property"}
      </Button>
    </div>
  );
}

// ─── POSITION SELECTOR ────────────────────────────────────────────────────────

function PositionSelector({
  titles,
  value,
  onChange,
}: {
  titles: Array<{ value: string; label: string }>;
  value: string;
  onChange: (v: string) => void;
}) {
  const isCustom = Boolean(value && !titles.find((t) => t.value === value && t.value !== "__custom__"));
  const [showCustom, setShowCustom] = useState(isCustom);
  const [customVal, setCustomVal] = useState(isCustom ? value : "");
  const [selectVal, setSelectVal] = useState(isCustom ? "__custom__" : value);

  const handleSelect = (v: string) => {
    setSelectVal(v);
    if (v === "__custom__") { setShowCustom(true); onChange(customVal); }
    else { setShowCustom(false); onChange(v); }
  };

  return (
    <div className="space-y-2">
      <Select value={selectVal} onValueChange={handleSelect}>
        <SelectTrigger data-testid="select-position"><SelectValue placeholder="Select position…" /></SelectTrigger>
        <SelectContent>
          {titles.map((t) => (
            <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
          ))}
        </SelectContent>
      </Select>
      {showCustom && (
        <Input
          placeholder="Enter custom position title"
          value={customVal}
          data-testid="input-position-custom"
          onChange={(e) => { setCustomVal(e.target.value); onChange(e.target.value); }}
        />
      )}
    </div>
  );
}

// ─── STEP 1 ───────────────────────────────────────────────────────────────────

function Step1({
  contractType, setContractType,
  department, setDepartment,
  languages, setLanguages,
  onNext,
}: {
  contractType: "employment" | "b2b"; setContractType: (v: "employment" | "b2b") => void;
  department: string; setDepartment: (v: string) => void;
  languages: string[]; setLanguages: (v: string[]) => void;
  onNext: () => void;
}) {
  const toggleLang = (l: string) =>
    setLanguages(languages.includes(l) ? languages.filter((x) => x !== l) : [...languages, l]);

  return (
    <div className="fade-up space-y-6">
      <div>
        <SectionHead>Contract Type / ประเภทสัญญา / စာချုပ်အမျိုးအစား</SectionHead>
        <div className="grid grid-cols-2 gap-4">
          {[
            { key: "employment", icon: <Briefcase className="w-6 h-6" />, en: "Employment Agreement", th: "สัญญาจ้างงาน", my: "အလုပ်ခန့်စာချုပ်", desc: "For MPS payroll staff" },
            { key: "b2b",        icon: <Users className="w-6 h-6" />,     en: "B2B Collaboration",   th: "ความร่วมมือ B2B",  my: "B2B ပူးပေါင်းဆောင်ရွက်", desc: "Adam, Chen, Phyo & partners" },
          ].map((c) => (
            <div key={c.key} className={`dept-card ${contractType === c.key ? "active" : ""}`}
              onClick={() => setContractType(c.key as "employment" | "b2b")} data-testid={`card-contract-${c.key}`}>
              <div className="flex justify-center mb-3">{c.icon}</div>
              <div className="font-bold text-sm">{c.en}</div>
              <div className="text-xs mt-1" style={{ opacity: 0.75 }}>{c.th}</div>
              <div className="text-xs" style={{ opacity: 0.65, fontFamily: "'Noto Sans Myanmar', sans-serif" }}>{c.my}</div>
              <div className="text-xs mt-2" style={{ opacity: 0.6 }}>{c.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {contractType === "employment" && (
        <div>
          <SectionHead>Department / แผนก / ဌာန</SectionHead>
          <div className="grid grid-cols-3 gap-3 items-stretch">
            {[
              { key: "housekeeping",        icon: <Home className="w-5 h-5" />,     en: "Housekeeping",             th: "แม่บ้าน",             my: "အိမ်သာ" },
              { key: "office",              icon: <Building2 className="w-5 h-5" />, en: "Office / Management",      th: "สำนักงาน / บริหาร",   my: "ရုံး / စီမံ" },
              { key: "pool_garden_handyman",icon: <Wrench className="w-5 h-5" />,   en: "Pool, Garden & Handyman",  th: "สระ / สวน / ช่าง",    my: "ရေကူး / ဥယျာဉ် / ဆရာ" },
            ].map((d) => (
              <div key={d.key}
                className={`dept-card flex flex-col items-center ${department === d.key ? "active" : ""}`}
                onClick={() => setDepartment(d.key)} data-testid={`card-dept-${d.key}`} style={{ minHeight: 110 }}>
                <div className="flex justify-center mb-2">{d.icon}</div>
                <div className="font-semibold text-xs">{d.en}</div>
                <div className="text-xs mt-1" style={{ opacity: 0.75, fontFamily: "'Noto Sans Thai', sans-serif" }}>{d.th}</div>
                <div className="text-xs" style={{ opacity: 0.65, fontFamily: "'Noto Sans Myanmar', sans-serif" }}>{d.my}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        <SectionHead>Contract Languages / ภาษาของสัญญา / စာချုပ်ဘာသာ</SectionHead>
        <div className="flex flex-wrap gap-3">
          {[
            { key: "en", label: "English",  sub: "อังกฤษ / အင်္ဂလိပ်" },
            { key: "th", label: "Thai",     sub: "ภาษาไทย / ထိုင်း" },
            { key: "my", label: "Burmese",  sub: "ภาษาพม่า / မြန်မာ" },
          ].map((l) => (
            <label key={l.key} className={`addon-card flex items-center gap-3 cursor-pointer min-w-[140px] ${languages.includes(l.key) ? "selected" : ""}`}
              data-testid={`check-lang-${l.key}`}>
              <Checkbox checked={languages.includes(l.key)} onCheckedChange={() => toggleLang(l.key)} className="shrink-0" />
              <div>
                <div className="font-semibold text-sm">{l.label}</div>
                <div className="text-xs" style={{ color: "hsl(var(--muted-foreground))" }}>{l.sub}</div>
              </div>
            </label>
          ))}
        </div>
        {languages.length === 0 && (
          <p className="text-sm mt-2" style={{ color: "hsl(var(--destructive))" }}>Select at least one language.</p>
        )}
      </div>

      <Button className="w-full btn-generate" onClick={onNext} disabled={languages.length === 0} data-testid="button-step1-next">
        Continue — Personnel Details <ChevronRight className="w-4 h-4 ml-1" />
      </Button>
    </div>
  );
}

// ─── MULTI-ROLE CHIP SELECTOR ────────────────────────────────────────────────

function MultiRoleSelector({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  const [custom, setCustom] = useState("");

  const grouped: Record<string, typeof B2B_TITLES> = {};
  for (const t of B2B_TITLES.filter(t => t.value !== "__custom__")) {
    const g = t.group ?? "Other";
    if (!grouped[g]) grouped[g] = [];
    grouped[g].push(t);
  }

  const toggle = (v: string) =>
    onChange(value.includes(v) ? value.filter(x => x !== v) : [...value, v]);

  const addCustom = () => {
    const t = custom.trim();
    if (t && !value.includes(t)) { onChange([...value, t]); setCustom(""); }
  };

  return (
    <div className="space-y-3">
      {/* Selected chips */}
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {value.map(v => (
            <span key={v} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold"
              style={{ background: "var(--gold)", color: "#fff" }}>
              {v}
              <button type="button" onClick={() => toggle(v)} className="ml-0.5 opacity-80 hover:opacity-100">×</button>
            </span>
          ))}
        </div>
      )}
      {/* Grouped toggle chips */}
      <div className="space-y-2">
        {Object.entries(grouped).map(([group, titles]) => (
          <div key={group}>
            <p className="text-xs font-semibold mb-1.5" style={{ color: "hsl(var(--muted-foreground))" }}>{group}</p>
            <div className="flex flex-wrap gap-1.5">
              {titles.map(t => {
                const selected = value.includes(t.value);
                return (
                  <button key={t.value} type="button"
                    onClick={() => toggle(t.value)}
                    className="px-2.5 py-1 rounded-full text-xs border transition-all"
                    style={{
                      background: selected ? "var(--navy)" : "transparent",
                      color: selected ? "#fff" : "hsl(var(--foreground))",
                      borderColor: selected ? "var(--navy)" : "hsl(var(--border))",
                    }}
                    data-testid={`role-chip-${t.value}`}
                  >
                    {selected && "✓ "}{t.label}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
      {/* Custom input */}
      <div className="flex gap-2">
        <Input placeholder="Custom role / service title…" value={custom}
          onChange={e => setCustom(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); addCustom(); }}}
          data-testid="input-role-custom" />
        <Button type="button" variant="outline" size="sm" onClick={addCustom} data-testid="btn-add-role">
          <Plus className="w-3.5 h-3.5 mr-1" /> Add
        </Button>
      </div>
    </div>
  );
}

// ─── ROLE CHIP INPUT (for employment additional roles) ────────────────────────

function RoleChipInput({ value, onChange, placeholder }: {
  value: string[];
  onChange: (v: string[]) => void;
  placeholder?: string;
}) {
  const [input, setInput] = useState("");
  const add = () => {
    const t = input.trim();
    if (t && !value.includes(t)) { onChange([...value, t]); setInput(""); }
  };
  return (
    <div className="space-y-2">
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {value.map(v => (
            <span key={v} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold"
              style={{ background: "var(--navy)", color: "#fff" }}>
              {v}
              <button type="button" onClick={() => onChange(value.filter(x => x !== v))} className="ml-0.5 opacity-80 hover:opacity-100">×</button>
            </span>
          ))}
        </div>
      )}
      <div className="flex gap-2">
        <Input value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); add(); }}}
          placeholder={placeholder ?? "e.g. Concierge Provider"} data-testid="input-additional-role" />
        <Button type="button" variant="outline" size="sm" onClick={add} data-testid="btn-add-additional-role">
          <Plus className="w-3.5 h-3.5 mr-1" /> Add
        </Button>
      </div>
    </div>
  );
}

// ─── STEP 2: EMPLOYMENT ───────────────────────────────────────────────────────

function Step2Employment({
  form, department, empProperties, setEmpProperties, additionalRoles, setAdditionalRoles,
}: {
  form: ReturnType<typeof useForm<EmployeeData>>;
  department: string;
  empProperties: ManagedProperty[];
  setEmpProperties: (v: ManagedProperty[]) => void;
  additionalRoles: string[];
  setAdditionalRoles: (v: string[]) => void;
}) {
  const isManager = ["office"].includes(department);

  const addRow = () => setEmpProperties([...empProperties, { propertyName: "", managementPackRate: 0, commissionRate: 0 }]);
  const removeRow = (i: number) => setEmpProperties(empProperties.filter((_, idx) => idx !== i));
  const updateRow = (i: number, field: "propertyName" | "managementPackRate" | "commissionRate", val: string | number) => {
    const next = [...empProperties];
    if (field === "propertyName") next[i].propertyName = String(val);
    else if (field === "managementPackRate") next[i].managementPackRate = Number(val);
    else next[i].commissionRate = Number(val);
    setEmpProperties(next);
  };

  return (
    <Form {...form}>
      <div className="fade-up space-y-5">
        <SectionHead>Employee Details / ข้อมูลพนักงาน / ဝန်ထမ်းအချက်အလက်</SectionHead>

        {/* Full Name + Nickname */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <FormField control={form.control} name="fullName" render={({ field }) => (
            <FormItem>
              <TriLabel en="Full Name" th="ชื่อ-นามสกุล" my="အမည်" />
              <FormControl><Input {...field} data-testid="input-emp-fullName" /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="nickname" render={({ field }) => (
            <FormItem>
              <TriLabel en="Nickname" th="ชื่อเล่น" my="နာမည်တိုဆိုင်ရာ" />
              <FormControl><Input {...field} placeholder="e.g. Bee, Adam, Noi" data-testid="input-emp-nickname" /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="dateOfBirth" render={({ field }) => (
            <FormItem>
              <TriLabel en="Date of Birth" th="วันเดือนปีเกิด" my="မွေးသက္ကရာဇ်" />
              <FormControl><Input type="date" {...field} data-testid="input-emp-dob" /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
        </div>

        {/* Position */}
        <div>
          <TriLabel en="Position / Title" th="ตำแหน่ง" my="ရာထူး" />
          <FormField control={form.control} name="position" render={({ field }) => (
            <FormItem>
              <FormControl>
                <PositionSelector
                  titles={EMP_TITLES[department] ?? EMP_TITLES.office}
                  value={field.value ?? ""}
                  onChange={field.onChange}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )} />
        </div>

        {/* Nationality + ID */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <FormField control={form.control} name="nationality" render={({ field }) => (
            <FormItem>
              <TriLabel en="Nationality" th="สัญชาติ" my="နိုင်ငံသား" />
              <FormControl><Input {...field} data-testid="input-emp-nationality" /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="idPassport" render={({ field }) => (
            <FormItem>
              <TriLabel en="ID / Passport No." th="เลขที่บัตร / หนังสือเดินทาง" my="မှတ်ပုံတင် / ပတ်စ်ပို့" />
              <FormControl><Input {...field} data-testid="input-emp-idPassport" /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
        </div>

        {/* Address */}
        <FormField control={form.control} name="address" render={({ field }) => (
          <FormItem>
            <TriLabel en="Address" th="ที่อยู่" my="လိပ်စာ" />
            <FormControl><Textarea {...field} rows={2} data-testid="input-emp-address" /></FormControl>
            <FormMessage />
          </FormItem>
        )} />

        {/* Phone + Salary + Start Date */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <FormField control={form.control} name="phone" render={({ field }) => (
            <FormItem>
              <TriLabel en="Phone" th="โทรศัพท์" my="ဖုန်းနံပါတ်" />
              <FormControl><Input {...field} data-testid="input-emp-phone" /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="salary" render={({ field }) => (
            <FormItem>
              <TriLabel en="Monthly Salary (THB)" th="เงินเดือน (บาท)" my="လစာ (THB)" />
              <FormControl><Input {...field} type="number" value={field.value?.toString() ?? ""} data-testid="input-emp-salary" /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
          <FormField control={form.control} name="startDate" render={({ field }) => (
            <FormItem>
              <TriLabel en="Start Date" th="วันที่เริ่มงาน" my="အလုပ်စတင်သောနေ့" />
              <FormControl><Input {...field} type="date" data-testid="input-emp-startDate" /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
        </div>

        {/* Additional Roles / Scope of Work */}
        <div className="rounded-lg p-4 space-y-2" style={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))"}}>
          <div>
            <p className="font-semibold text-sm" style={{ color: "var(--navy)", fontFamily: "'Playfair Display', Georgia, serif" }}>
              Additional Scope of Work / ขอบเขตงานเพิ่มเติม / နောက်ထပ်တာဝန်များ
            </p>
            <p className="text-xs mt-0.5" style={{ color: "hsl(var(--muted-foreground))" }}>
              Add extra roles or services this employee also covers — e.g. Concierge Provider, Chef Service Coordinator.
            </p>
          </div>
          <RoleChipInput value={additionalRoles} onChange={setAdditionalRoles}
            placeholder="e.g. Concierge Provider" />
        </div>

        {/* Properties managed (always visible, label varies) */}
        <div className="rounded-lg p-4 space-y-3" style={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }}>
          <div>
            <p className="font-semibold text-sm" style={{ color: "var(--navy)", fontFamily: "'Playfair Display', Georgia, serif" }}>
              Properties Managed + Management Pack %
            </p>
            <p className="text-xs mt-0.5" style={{ color: "hsl(var(--muted-foreground))" }}>
              {isManager
                ? "Required for managers: list each villa and its dedicated management pack percentage (paid on top of base salary)."
                : "Optional: specify if this role carries responsibility for specific villas and their management pack %."}
            </p>
          </div>
          <PropertyTable
            rows={empProperties}
            onAdd={addRow}
            onRemove={removeRow}
            onUpdate={updateRow}
            placeholder="Add each villa this employee manages."
            label="Property"
            packLabel="Mgmt Pack %"
            rateLabel="Cut of Pack %"
          />
        </div>
      </div>
    </Form>
  );
}

// ─── STEP 2: B2B ─────────────────────────────────────────────────────────────

function Step2B2B({
  form, colProperties, setColProperties, colRoles, setColRoles,
}: {
  form: ReturnType<typeof useForm<CollaboratorData>>;
  colProperties: B2BProperty[];
  setColProperties: (v: B2BProperty[]) => void;
  colRoles: string[];
  setColRoles: (v: string[]) => void;
}) {
  const isCompany = form.watch("isCompany");

  const addRow = () => setColProperties([...colProperties, { propertyName: "", managementPackRate: 0, commissionRate: 0 }]);
  const removeRow = (i: number) => setColProperties(colProperties.filter((_, idx) => idx !== i));
  const updateRow = (i: number, field: "propertyName" | "managementPackRate" | "commissionRate", val: string | number) => {
    const next = [...colProperties];
    if (field === "propertyName") next[i].propertyName = String(val);
    else if (field === "managementPackRate") next[i].managementPackRate = Number(val);
    else next[i].commissionRate = Number(val);
    setColProperties(next);
  };

  return (
    <Form {...form}>
      <div className="fade-up space-y-5">
        <SectionHead>Collaborator Details / ข้อมูลผู้ร่วมงาน / ပူးပေါင်းသူ အချက်အလက်</SectionHead>

        {/* Individual / Company toggle */}
        <div className="flex gap-3">
          {[
            { key: false, icon: <User className="w-4 h-4" />, label: "Individual",  sub: "Personal agreement" },
            { key: true,  icon: <Building className="w-4 h-4" />, label: "Company", sub: "Registered company" },
          ].map((opt) => (
            <button key={String(opt.key)} type="button"
              className={`flex-1 flex items-center gap-3 p-3 rounded-lg border-2 text-left transition-all ${isCompany === opt.key ? "border-[var(--gold)] bg-[rgba(155,126,82,0.08)]" : "border-[hsl(var(--border))]"}`}
              onClick={() => form.setValue("isCompany", opt.key as boolean)}
              data-testid={`btn-is-company-${String(opt.key)}`}>
              <div className="shrink-0" style={{ color: isCompany === opt.key ? "var(--gold)" : "hsl(var(--muted-foreground))" }}>
                {opt.icon}
              </div>
              <div>
                <div className="text-sm font-semibold">{opt.label}</div>
                <div className="text-xs" style={{ color: "hsl(var(--muted-foreground))" }}>{opt.sub}</div>
              </div>
            </button>
          ))}
        </div>

        {/* Company details block */}
        {isCompany && (
          <div className="rounded-lg p-4 space-y-4" style={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }}>
            <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--gold)" }}>Company Information</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FormField control={form.control} name="companyName" render={({ field }) => (
                <FormItem className="sm:col-span-2">
                  <TriLabel en="Legal Company Name" th="ชื่อบริษัทตามกฎหมาย" my="ကုမ္ပဏီ တရားဝင်နာမည်" />
                  <FormControl><Input {...field} placeholder="e.g. Adam Properties Co., Ltd." data-testid="input-b2b-companyName" /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="companyRegistration" render={({ field }) => (
                <FormItem>
                  <TriLabel en="Company Reg. No." th="เลขทะเบียนบริษัท" my="ကုမ္ပဏီ မှတ်ပုံတင်နံပါတ်" />
                  <FormControl><Input {...field} placeholder="e.g. 0105565012345" data-testid="input-b2b-companyRegistration" /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="companyTaxId" render={({ field }) => (
                <FormItem>
                  <TriLabel en="Tax ID / VAT No." th="เลขประจำตัวผู้เสียภาษี" my="အခွန်နံပါတ်" />
                  <FormControl><Input {...field} placeholder="e.g. 0105565012345" data-testid="input-b2b-companyTaxId" /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="companyAddress" render={({ field }) => (
                <FormItem className="sm:col-span-2">
                  <TriLabel en="Registered Company Address" th="ที่อยู่จดทะเบียนบริษัท" my="ကုမ္ပဏီ မှတ်ပုံတင်လိပ်စာ" />
                  <FormControl><Textarea {...field} rows={2} data-testid="input-b2b-companyAddress" /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
            </div>
          </div>
        )}

        {/* Personal details */}
        <div className="space-y-4">
          <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--gold)" }}>
            {isCompany ? "Authorised Representative" : "Personal Details"}
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <FormField control={form.control} name="fullName" render={({ field }) => (
              <FormItem>
                <TriLabel en="Full Name" th="ชื่อ-นามสกุล" my="အမည်" />
                <FormControl><Input {...field} data-testid="input-b2b-fullName" /></FormControl>
                <FormMessage />
              </FormItem>
            )} />
            <FormField control={form.control} name="nickname" render={({ field }) => (
              <FormItem>
                <TriLabel en="Nickname" th="ชื่อเล่น" my="နာမည်တိုဆိုင်ရာ" />
                <FormControl><Input {...field} placeholder="e.g. Adam, Chen, Phyo" data-testid="input-b2b-nickname" /></FormControl>
                <FormMessage />
              </FormItem>
            )} />
            <FormField control={form.control} name="dateOfBirth" render={({ field }) => (
              <FormItem>
                <TriLabel en="Date of Birth" th="วันเดือนปีเกิด" my="မွေးသက္ကရာဇ်" />
                <FormControl><Input type="date" {...field} data-testid="input-b2b-dob" /></FormControl>
                <FormMessage />
              </FormItem>
            )} />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <FormField control={form.control} name="idPassport" render={({ field }) => (
              <FormItem>
                <TriLabel en="ID / Passport No." th="เลขที่บัตร / หนังสือเดินทาง" my="မှတ်ပုံတင် / ပတ်စ်ပို့" />
                <FormControl><Input {...field} data-testid="input-b2b-idPassport" /></FormControl>
                <FormMessage />
              </FormItem>
            )} />
            <FormField control={form.control} name="phone" render={({ field }) => (
              <FormItem>
                <TriLabel en="Phone" th="โทรศัพท์" my="ဖုန်းနံပါတ်" />
                <FormControl><Input {...field} data-testid="input-b2b-phone" /></FormControl>
                <FormMessage />
              </FormItem>
            )} />
          </div>

          <FormField control={form.control} name="email" render={({ field }) => (
            <FormItem>
              <TriLabel en="Email" th="อีเมล" my="အီးမေးလ်" />
              <FormControl><Input {...field} type="email" data-testid="input-b2b-email" /></FormControl>
              <FormMessage />
            </FormItem>
          )} />
        </div>

        {/* Roles — multi-select */}
        <div className="rounded-lg p-4 space-y-3" style={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))"}}>
          <div>
            <p className="font-semibold text-sm" style={{ color: "var(--navy)", fontFamily: "'Playfair Display', Georgia, serif" }}>
              Roles / Collaboration Type / ประเภทความร่วมมือ / ပူးပေါင်းဆောင်ရွက်မှုအမျိုးအစား
            </p>
            <p className="text-xs mt-0.5" style={{ color: "hsl(var(--muted-foreground))" }}>
              Select all that apply — e.g. Villa Manager + Chef Service + Cleaning Team.
            </p>
          </div>
          <MultiRoleSelector value={colRoles} onChange={setColRoles} />
        </div>

        {/* Services */}
        <FormField control={form.control} name="services" render={({ field }) => (
          <FormItem>
            <TriLabel en="Services / Scope of Work" th="บริการ / ขอบเขตงาน" my="ဝန်ဆောင်မှု / လုပ်ငန်းနယ်ပယ်" />
            <FormControl>
              <Textarea {...field} rows={4} placeholder="Describe exactly what services this collaborator provides to MPS…" data-testid="input-b2b-services" />
            </FormControl>
            <FormMessage />
          </FormItem>
        )} />

        {/* Property-specific commission */}
        <div className="rounded-lg p-4 space-y-3" style={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }}>
          <div>
            <p className="font-semibold text-sm" style={{ color: "var(--navy)", fontFamily: "'Playfair Display', Georgia, serif" }}>
              Commission by Property
            </p>
            <p className="text-xs mt-0.5" style={{ color: "hsl(var(--muted-foreground))" }}>
              Specify commission rate per property/villa. Different rates are supported. A general fallback rate can be added below.
            </p>
          </div>
          <PropertyTable
            rows={colProperties}
            onAdd={addRow}
            onRemove={removeRow}
            onUpdate={updateRow}
            placeholder="Add each villa/property with its management pack % and your commission cut."
            label="Property"
            packLabel="Mgmt Pack %"
            rateLabel="Cut of Pack %"
          />
          {/* General fallback rate */}
          <div className="flex items-center gap-3 pt-1">
            <span className="text-sm shrink-0" style={{ color: "hsl(var(--muted-foreground))" }}>General / fallback rate:</span>
            <div className="relative w-28">
              <FormField control={form.control} name="commissionRate" render={({ field }) => (
                <FormItem>
                  <FormControl>
                    <Input {...field} type="number" min={0} max={100} className="pr-6"
                      value={field.value?.toString() ?? ""}
                      placeholder="0"
                      data-testid="input-b2b-commissionRate" />
                  </FormControl>
                </FormItem>
              )} />
              <span className="absolute right-2 top-1/2 -translate-y-1/2 text-sm pointer-events-none" style={{ color: "hsl(var(--muted-foreground))" }}>%</span>
            </div>
          </div>
        </div>

        {/* Payment terms */}
        <FormField control={form.control} name="paymentTerms" render={({ field }) => (
          <FormItem>
            <TriLabel en="Payment Terms" th="เงื่อนไขการชำระเงิน" my="ငွေပေးချေမှုစည်းကမ်း" />
            <FormControl>
              <Select value={field.value} onValueChange={field.onChange}>
                <SelectTrigger data-testid="select-payment-terms"><SelectValue placeholder="Select payment terms…" /></SelectTrigger>
                <SelectContent>
                  {["Monthly (end of month)","Monthly (15th)","Bi-monthly","Quarterly","Per booking / transaction","Upon invoice","Custom"].map((t) => (
                    <SelectItem key={t} value={t}>{t}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormControl>
            <FormMessage />
          </FormItem>
        )} />
      </div>
    </Form>
  );
}

// ─── STEP 3 ───────────────────────────────────────────────────────────────────

function DutyCheckbox({ dutyKey, checked, onToggle }: { dutyKey: string; checked: boolean; onToggle: () => void }) {
  const labels = DUTY_LABELS[dutyKey];
  if (!labels) return null;
  return (
    <label className={`addon-card flex items-start gap-3 cursor-pointer ${checked ? "selected" : ""}`} data-testid={`check-duty-${dutyKey}`}>
      <Checkbox checked={checked} onCheckedChange={onToggle} className="shrink-0 mt-0.5" />
      <div>
        <div className="font-medium text-sm leading-tight">{labels.en}</div>
        <div className="text-xs mt-0.5 leading-tight" style={{ color: "hsl(var(--muted-foreground))", fontFamily: "'Noto Sans Thai', sans-serif" }}>{labels.th}</div>
        <div className="text-xs leading-tight" style={{ color: "hsl(var(--muted-foreground))", fontFamily: "'Noto Sans Myanmar', sans-serif" }}>{labels.my}</div>
      </div>
    </label>
  );
}

function Step3({
  contractType, department, selectedDuties, setSelectedDuties, selectedComplicated, setSelectedComplicated,
}: {
  contractType: "employment" | "b2b"; department: string;
  selectedDuties: string[]; setSelectedDuties: (v: string[]) => void;
  selectedComplicated: string[]; setSelectedComplicated: (v: string[]) => void;
}) {
  const deptDuties = DEPT_DUTIES[department] ?? [];
  const toggle = (key: string, arr: string[], setter: (v: string[]) => void) =>
    setter(arr.includes(key) ? arr.filter((k) => k !== key) : [...arr, key]);

  return (
    <div className="fade-up space-y-6">
      {contractType === "employment" && (
        <div>
          <SectionHead>Additional Duties / หน้าที่เพิ่มเติม / ထပ်ဆောင်း တာဝန်</SectionHead>
          <p className="text-sm mb-4" style={{ color: "hsl(var(--muted-foreground))" }}>
            Select any additional responsibilities to include in Annex A. Core duties are already included by default.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {deptDuties.map((key) => (
              <DutyCheckbox key={key} dutyKey={key} checked={selectedDuties.includes(key)}
                onToggle={() => toggle(key, selectedDuties, setSelectedDuties)} />
            ))}
          </div>
        </div>
      )}

      <div>
        <SectionHead>Complicated Functions / ฟังก์ชันพิเศษ / အထူးတာဝန်</SectionHead>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {COMPLICATED_KEYS.map((key) => (
            <DutyCheckbox key={key} dutyKey={key} checked={selectedComplicated.includes(key)}
              onToggle={() => toggle(key, selectedComplicated, setSelectedComplicated)} />
          ))}
        </div>
      </div>

      <div className="rounded-lg p-4 text-sm" style={{ background: "rgba(155,126,82,0.08)", border: "1px solid rgba(155,126,82,0.3)" }}>
        <p className="font-semibold mb-1" style={{ color: "var(--gold)" }}>Uniform Policy (included in all contracts)</p>
        <p style={{ color: "hsl(var(--foreground))" }}>
          MPS provides three (3) complete uniform sets upon signing. Replacement due to loss or damage within the same year is at the employee's own cost. Sets are renewed once a year on the employment anniversary.
        </p>
        <p className="mt-1" style={{ color: "hsl(var(--muted-foreground))", fontFamily: "'Noto Sans Thai', sans-serif", fontSize: "0.78rem" }}>
          MPS จัดชุดทำงาน 3 ชุดเมื่อเซ็นสัญญา หากสูญหายหรือเสียหายภายในปีเดียวกันต้องออกค่าใช้จ่ายเอง ชุดทำงานจะต่อสิทธิ์ปีละหนึ่งครั้ง
        </p>
      </div>
    </div>
  );
}

// ─── STEP 4: SUMMARY ─────────────────────────────────────────────────────────

function SummaryRow({ label, value }: { label: string; value?: string | number }) {
  if (!value && value !== 0) return null;
  return (
    <div className="flex justify-between items-start py-2 border-b" style={{ borderColor: "hsl(var(--border))" }}>
      <span className="text-sm font-medium shrink-0 mr-4" style={{ color: "hsl(var(--muted-foreground))", minWidth: 130 }}>{label}</span>
      <span className="text-sm text-right" style={{ color: "hsl(var(--foreground))" }}>{value}</span>
    </div>
  );
}

function Step4({
  contractType, department, languages, employeeForm, collaboratorForm,
  selectedDuties, selectedComplicated, empProperties, colProperties,
  empAdditionalRoles, colRoles,
  onGenerate, isPending,
}: {
  contractType: "employment" | "b2b"; department: string; languages: string[];
  employeeForm: ReturnType<typeof useForm<EmployeeData>>;
  collaboratorForm: ReturnType<typeof useForm<CollaboratorData>>;
  selectedDuties: string[]; selectedComplicated: string[];
  empProperties: ManagedProperty[]; colProperties: B2BProperty[];
  empAdditionalRoles: string[]; colRoles: string[];
  onGenerate: () => void; isPending: boolean;
}) {
  const emp = employeeForm.getValues();
  const b2b = collaboratorForm.getValues();
  const langLabels: Record<string, string> = { en: "English", th: "Thai", my: "Burmese" };
  const deptLabels: Record<string, string> = { housekeeping: "Housekeeping", office: "Office / Management", pool_garden_handyman: "Pool, Garden & Handyman" };

  return (
    <div className="fade-up space-y-6">
      <SectionHead>Review & Generate / ตรวจสอบและสร้าง / စစ်ဆေးပြီး ထုတ်လုပ်</SectionHead>

      <div className="rounded-lg p-4" style={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }}>
        <div className="font-semibold text-sm mb-2" style={{ color: "var(--navy)", fontFamily: "'Playfair Display', Georgia, serif" }}>Contract Setup</div>
        <SummaryRow label="Type" value={contractType === "employment" ? "Employment Agreement" : "B2B Collaboration"} />
        {contractType === "employment" && <SummaryRow label="Department" value={deptLabels[department]} />}
        <SummaryRow label="Languages" value={languages.map((l) => langLabels[l]).join(", ")} />
      </div>

      <div className="rounded-lg p-4" style={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }}>
        <div className="font-semibold text-sm mb-2" style={{ color: "var(--navy)", fontFamily: "'Playfair Display', Georgia, serif" }}>
          {contractType === "employment" ? "Employee" : "Collaborator"}
        </div>
        {contractType === "employment" ? (
          <>
            <SummaryRow label="Full name" value={emp.fullName} />
            {emp.nickname && <SummaryRow label="Nickname" value={emp.nickname} />}
            <SummaryRow label="Nationality" value={emp.nationality} />
            <SummaryRow label="ID / Passport" value={emp.idPassport} />
            <SummaryRow label="Position" value={emp.position} />
            {empAdditionalRoles.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-1">
                {empAdditionalRoles.map((r,i) => <span key={i} className="gold-pill">{r}</span>)}
              </div>
            )}
            <SummaryRow label="Salary (THB)" value={emp.salary ? `฿${Number(emp.salary).toLocaleString()}` : undefined} />
            <SummaryRow label="Start date" value={emp.startDate} />
            {empProperties.length > 0 && (
              <div className="pt-2">
                <div className="text-xs font-medium mb-1" style={{ color: "hsl(var(--muted-foreground))" }}>Managed Properties</div>
                <div className="flex flex-wrap gap-1">
                  {empProperties.map((p, i) => (
                    <span key={i} className="gold-pill">{p.propertyName} — Pack {p.managementPackRate ?? "?"}% / Cut {p.commissionRate}%</span>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <>
            {b2b.isCompany && <SummaryRow label="Company" value={b2b.companyName} />}
            {b2b.isCompany && <SummaryRow label="Reg. No." value={b2b.companyRegistration} />}
            <SummaryRow label="Full name" value={b2b.fullName} />
            {b2b.nickname && <SummaryRow label="Nickname" value={b2b.nickname} />}
            {colRoles.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-1">
                {colRoles.map((r,i) => <span key={i} className="gold-pill">{r}</span>)}
              </div>
            )}
            <SummaryRow label="Email" value={b2b.email} />
            <SummaryRow label="Payment terms" value={b2b.paymentTerms} />
            {colProperties.length > 0 && (
              <div className="pt-2">
                <div className="text-xs font-medium mb-1" style={{ color: "hsl(var(--muted-foreground))" }}>Commission by Property</div>
                <div className="flex flex-wrap gap-1">
                  {colProperties.map((p, i) => (
                    <span key={i} className="gold-pill">{p.propertyName} — Pack {p.managementPackRate ?? "?"}% / Cut {p.commissionRate}%</span>
                  ))}
                </div>
                {(b2b.commissionRate ?? 0) > 0 && (
                  <div className="text-xs mt-1" style={{ color: "hsl(var(--muted-foreground))" }}>
                    General rate: {b2b.commissionRate}%
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>

      {(selectedDuties.length > 0 || selectedComplicated.length > 0) && (
        <div className="rounded-lg p-4" style={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))" }}>
          <div className="font-semibold text-sm mb-2" style={{ color: "var(--navy)", fontFamily: "'Playfair Display', Georgia, serif" }}>Add-ons Selected</div>
          {selectedDuties.length > 0 && (
            <div className="mb-2">
              <div className="text-xs font-medium mb-1" style={{ color: "hsl(var(--muted-foreground))" }}>Duties</div>
              <div className="flex flex-wrap gap-1">{selectedDuties.map((k) => <span key={k} className="gold-pill">{DUTY_LABELS[k]?.en}</span>)}</div>
            </div>
          )}
          {selectedComplicated.length > 0 && (
            <div>
              <div className="text-xs font-medium mb-1" style={{ color: "hsl(var(--muted-foreground))" }}>Complicated Functions</div>
              <div className="flex flex-wrap gap-1">{selectedComplicated.map((k) => <span key={k} className="gold-pill">{DUTY_LABELS[k]?.en}</span>)}</div>
            </div>
          )}
        </div>
      )}

      <div className="rounded-lg p-4 text-sm space-y-1" style={{ background: "rgba(28,35,64,0.05)", border: "1px solid rgba(28,35,64,0.15)" }}>
        <p className="font-semibold" style={{ color: "var(--navy)" }}>Your ZIP will contain:</p>
        {languages.map((l) => (
          <div key={l} className="flex items-center gap-2">
            <FileText className="w-3 h-3 shrink-0" style={{ color: "var(--gold)" }} />
            <span style={{ color: "hsl(var(--foreground))" }}>
              {langLabels[l]}: {contractType === "employment"
                ? "Employment Agreement + Annex A (duties) + Annex B (bonus)"
                : "B2B Collaboration Agreement"}
            </span>
          </div>
        ))}
      </div>

      <button className="btn-generate w-full justify-center" onClick={onGenerate} disabled={isPending} data-testid="button-generate">
        {isPending ? (<><Loader2 className="w-5 h-5 animate-spin" />Generating contracts…</>) : (<><Download className="w-5 h-5" />Generate & Download ZIP</>)}
      </button>
    </div>
  );
}

// ─── SUCCESS ──────────────────────────────────────────────────────────────────

function SuccessScreen({ onReset }: { onReset: () => void }) {
  return (
    <div className="fade-up flex flex-col items-center text-center py-8 space-y-5">
      <div className="success-icon"><CheckCircle2 className="w-10 h-10 text-white" /></div>
      <h2 className="text-xl font-bold" style={{ color: "var(--navy)", fontFamily: "'Playfair Display', Georgia, serif" }}>Contracts Generated!</h2>
      <p className="text-sm max-w-xs" style={{ color: "hsl(var(--muted-foreground))" }}>
        Your PDF package downloaded as <b>MPS-Contracts.zip</b>.
      </p>
      <div className="rounded-lg p-4 text-sm max-w-sm w-full text-left space-y-1"
        style={{ background: "rgba(155,126,82,0.08)", border: "1px solid rgba(155,126,82,0.3)" }}>
        <p className="font-semibold mb-2" style={{ color: "var(--gold)" }}>Next steps</p>
        {["Print and review all documents","Attach Thai / Burmese translations","Collect signatures from both parties","File one copy per party"].map((s) => (
          <p key={s} style={{ color: "hsl(var(--foreground))" }}>• {s}</p>
        ))}
      </div>
      <Button variant="outline" onClick={onReset} data-testid="button-reset">
        <Plus className="w-4 h-4 mr-2" />Generate Another Contract
      </Button>
    </div>
  );
}

// ─── MAIN WIZARD ─────────────────────────────────────────────────────────────

export default function WizardPage() {
  const { toast } = useToast();

  // ── State ──────────────────────────────────────────────────────────────────
  const [step, setStep] = useState(1);
  const [contractType, setContractType] = useState<"employment" | "b2b">("employment");
  const [department, setDepartment] = useState("housekeeping");
  const [languages, setLanguages] = useState<string[]>(["en"]);
  const [selectedDuties, setSelectedDuties] = useState<string[]>([]);
  const [selectedComplicated, setSelectedComplicated] = useState<string[]>([]);
  const [empProperties, setEmpProperties] = useState<ManagedProperty[]>([]);
  const [empAdditionalRoles, setEmpAdditionalRoles] = useState<string[]>([]);
  const [colProperties, setColProperties] = useState<B2BProperty[]>([]);
  const [colRoles, setColRoles] = useState<string[]>([]);

  // ── Forms ──────────────────────────────────────────────────────────────────
  const employeeForm = useForm<EmployeeData>({
    resolver: zodResolver(employeeSchema),
    defaultValues: {
      fullName: "", nickname: "", nationality: "", idPassport: "",
      address: "", phone: "", position: "", salary: 0, startDate: "",
      managedProperties: [],
    },
  });

  const collaboratorForm = useForm<CollaboratorData>({
    resolver: zodResolver(collaboratorSchema),
    defaultValues: {
      fullName: "", nickname: "", isCompany: false,
      companyName: "", companyRegistration: "", companyTaxId: "", companyAddress: "",
      idPassport: "", phone: "", email: "",
      services: "", properties: [], commissionRate: 0, paymentTerms: "",
    },
  });

  // ── Generate mutation ──────────────────────────────────────────────────────
  const generateMutation = useMutation({
    mutationFn: async () => {
      const emp = employeeForm.getValues();
      const b2b = collaboratorForm.getValues();
      const payload = {
        contractType,
        department: contractType === "employment" ? department : undefined,
        languages,
        employee: contractType === "employment"
          ? { ...emp, managedProperties: empProperties, additionalRoles: empAdditionalRoles }
          : undefined,
        collaborator: contractType === "b2b"
          ? { ...b2b, properties: colProperties, roles: colRoles }
          : undefined,
        addons: { duties: selectedDuties, complicatedFunctions: selectedComplicated },
      };
      const res = await apiRequest("POST", "/api/generate", payload);
      const blob = await res.blob();
      return blob;
    },
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "MPS-Contracts.zip";
      document.body.appendChild(a); a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 5000);
      setStep(5);
    },
    onError: (err: Error) => {
      toast({ title: "Generation failed", description: err.message || "Please try again.", variant: "destructive" });
    },
  });

  // ── Navigation ─────────────────────────────────────────────────────────────
  const handleStep1Next = () => {
    if (languages.length === 0) { toast({ title: "Select a language", variant: "destructive" }); return; }
    setStep(2);
  };

  const handleStep2Next = async () => {
    const valid = contractType === "employment" ? await employeeForm.trigger() : await collaboratorForm.trigger();
    if (valid) setStep(3);
    else toast({ title: "Incomplete form", description: "Please fill in all required fields.", variant: "destructive" });
  };

  const handleReset = () => {
    setStep(1); setContractType("employment"); setDepartment("housekeeping");
    setLanguages(["en"]); setSelectedDuties([]); setSelectedComplicated([]);
    setEmpProperties([]); setEmpAdditionalRoles([]);
    setColProperties([]); setColRoles([]);
    employeeForm.reset(); collaboratorForm.reset();
  };

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen" style={{ background: "hsl(var(--background))" }}>
      <header className="mps-header sticky top-0 z-30" data-testid="mps-header">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center gap-3">
          <img src="/logo.jpg"
            alt="Mr Property Siam" className="h-9 w-auto" />
          <div>
            <div className="font-bold text-sm leading-tight" style={{ color: "var(--cream)", fontFamily: "'Playfair Display', Georgia, serif" }}>
              Contract Generator
            </div>
            <div className="text-xs flex items-center gap-1" style={{ color: "var(--gold)" }}>
              <Languages className="w-3 h-3" /> EN · TH · MY
            </div>
          </div>
        </div>
      </header>

      {step <= 4 && (
        <div className="max-w-3xl mx-auto" style={{ background: "hsl(var(--card))" }}>
          <StepBar step={step} />
        </div>
      )}

      <main className="max-w-3xl mx-auto px-4 py-8">
        {step === 1 && (
          <Step1
            contractType={contractType} setContractType={(v) => { setContractType(v); }}
            department={department} setDepartment={setDepartment}
            languages={languages} setLanguages={setLanguages}
            onNext={handleStep1Next}
          />
        )}

        {step === 2 && (
          <div>
            {contractType === "employment"
              ? <Step2Employment form={employeeForm} department={department} empProperties={empProperties} setEmpProperties={setEmpProperties} additionalRoles={empAdditionalRoles} setAdditionalRoles={setEmpAdditionalRoles} />
              : <Step2B2B form={collaboratorForm} colProperties={colProperties} setColProperties={setColProperties} colRoles={colRoles} setColRoles={setColRoles} />
            }
            <div className="flex gap-3 mt-6">
              <Button variant="outline" onClick={() => setStep(1)} data-testid="button-step2-back">
                <ChevronLeft className="w-4 h-4 mr-1" /> Back
              </Button>
              <Button className="flex-1 btn-generate" onClick={handleStep2Next} data-testid="button-step2-next">
                Continue — Add-ons <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div>
            <Step3
              contractType={contractType} department={department}
              selectedDuties={selectedDuties} setSelectedDuties={setSelectedDuties}
              selectedComplicated={selectedComplicated} setSelectedComplicated={setSelectedComplicated}
            />
            <div className="flex gap-3 mt-6">
              <Button variant="outline" onClick={() => setStep(2)} data-testid="button-step3-back">
                <ChevronLeft className="w-4 h-4 mr-1" /> Back
              </Button>
              <Button className="flex-1 btn-generate" onClick={() => setStep(4)} data-testid="button-step3-next">
                Review & Generate <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            </div>
          </div>
        )}

        {step === 4 && (
          <div>
            <Step4
              contractType={contractType} department={department} languages={languages}
              employeeForm={employeeForm} collaboratorForm={collaboratorForm}
              selectedDuties={selectedDuties} selectedComplicated={selectedComplicated}
              empProperties={empProperties} colProperties={colProperties}
              empAdditionalRoles={empAdditionalRoles} colRoles={colRoles}
              onGenerate={() => generateMutation.mutate()}
              isPending={generateMutation.isPending}
            />
            <div className="mt-4">
              <Button variant="outline" onClick={() => setStep(3)} disabled={generateMutation.isPending} data-testid="button-step4-back">
                <ChevronLeft className="w-4 h-4 mr-1" /> Back
              </Button>
            </div>
          </div>
        )}

        {step === 5 && <SuccessScreen onReset={handleReset} />}
      </main>
    </div>
  );
}
