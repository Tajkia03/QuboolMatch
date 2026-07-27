export interface CompletionSection {
  completed: number;
  total: number;
  percent: number;
}

export interface CompletionResult {
  overallPercent: number;
  sections: {
    personal: CompletionSection;
    health: CompletionSection;
    preferences: CompletionSection;
  };
}

type ProfileCompletionInput = Record<string, unknown>;

const parseArrayValue = (value: unknown): unknown[] | unknown => {
  if (Array.isArray(value)) {
    return value;
  }

  if (typeof value !== "string") {
    return value;
  }

  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed : value;
  } catch {
    return value;
  }
};

const pick = (profile: ProfileCompletionInput, camelKey: string, snakeKey: string) => {
  return profile[camelKey] ?? profile[snakeKey];
};

const isFilled = (value: unknown): boolean => {
  if (value === null || value === undefined) return false;
  if (typeof value === "string") return value.trim().length > 0;
  if (typeof value === "number") return Number.isFinite(value);
  if (typeof value === "boolean") return value === true;
  if (Array.isArray(value)) return value.length > 0;
  return false;
};

const getSectionCompletion = (fields: unknown[]): CompletionSection => {
  const total = fields.length;
  const completed = fields.filter(isFilled).length;
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0;
  return { completed, total, percent };
};

export const getProfileCompletion = (profile: ProfileCompletionInput): CompletionResult => {
  const longTermCondition = pick(profile, "longTermCondition", "long_term_condition");
  const disability = pick(profile, "disability", "disability");

  const personalFields = [
    pick(profile, "name", "name"),
    pick(profile, "age", "age"),
    pick(profile, "dateOfBirth", "date_of_birth"),
    pick(profile, "gender", "gender"),
    pick(profile, "address", "address"),
    pick(profile, "location", "location"),
    pick(profile, "religion", "religion"),
    pick(profile, "maritalStatus", "marital_status"),
    pick(profile, "academicBackground", "academic_background"),
    pick(profile, "profession", "profession"),
    pick(profile, "fatherName", "father_name"),
    pick(profile, "motherName", "mother_name"),
    pick(profile, "guardianName", "guardian_name"),
    pick(profile, "guardianRelation", "guardian_relation"),
    pick(profile, "guardianContactNumber", "guardian_contact_number")
  ];

  const healthFields = [
    pick(profile, "overallHealthStatus", "overall_health_status"),
    longTermCondition,
    longTermCondition === "Yes"
      ? pick(profile, "longTermConditionDescription", "long_term_condition_description")
      : longTermCondition,
    pick(profile, "bloodGroup", "blood_group"),
    parseArrayValue(pick(profile, "geneticConditions", "genetic_conditions")),
    pick(profile, "fertilityAwareness", "fertility_awareness"),
    disability,
    disability === "Yes"
      ? pick(profile, "disabilityDescription", "disability_description")
      : disability
  ];

  const preferenceFields = [
    pick(profile, "preferredAgeMin", "preferred_age_min"),
    pick(profile, "preferredAgeMax", "preferred_age_max"),
    pick(profile, "preferredReligion", "preferred_religion"),
    pick(profile, "preferredLocation", "preferred_location")
  ];

  const personal = getSectionCompletion(personalFields);
  const health = getSectionCompletion(healthFields);
  const preferences = getSectionCompletion(preferenceFields);

  const totalCompleted = personal.completed + health.completed + preferences.completed;
  const totalFields = personal.total + health.total + preferences.total;
  const overallPercent = totalFields > 0 ? Math.round((totalCompleted / totalFields) * 100) : 0;

  return {
    overallPercent,
    sections: {
      personal,
      health,
      preferences
    }
  };
};
