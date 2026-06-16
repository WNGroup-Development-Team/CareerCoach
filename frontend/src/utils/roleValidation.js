const RAW_VALID_ROLES = [
  "data analyst",
  "game design",
  "backend developer",
  "data scientist",
  "project manager",
  "software engineer",
  "frontend developer",
  "financial analyst",
  "accountant",
  "investment banker",
  "risk manager",
  "controller",
  "actuary",
  "economist",
  "auditor",
  "tax consultant",
  "portfolio manager",
  "mechanical engineer",
  "civil engineer",
  "electrical engineer",
  "structural engineer",
  "industrial engineer",
  "marketing manager",
  "digital marketer",
  "recruiter",
  "legal counsel",
  "ux designer",
  "supply chain manager",
  "cloud engineer",
  "cloud architect",
  "devops engineer",
  "site reliability engineer",
  "platform engineer",
  "kubernetes specialist",
  "devsecops engineer",
  "ml engineer",
  "deep learning engineer",
  "ai researcher",
  "mlops engineer",
  "ai product manager",
  "responsible ai specialist",
  "computer vision engineer",
  "image processing specialist",
  "robotics perception engineer",
  "autonomous systems engineer",
  "nlp engineer",
  "llm engineer",
  "conversational ai engineer",
  "speech recognition engineer",
  "data engineer",
  "big data engineer",
  "streaming data engineer",
  "analytics engineer",
  "cybersecurity analyst",
  "penetration tester",
  "security architect",
  "soc analyst",
  "embedded systems engineer",
  "iot engineer",
  "firmware engineer",
  "real time systems engineer",
  "network engineer",
  "network architect",
  "wireless engineer",
  "operations manager",
  "lean manager",
  "quality manager",
  "process engineer",
  "supply chain analyst",
  "logistics manager",
  "procurement manager",
  "erp specialist",
  "business analyst",
  "business intelligence analyst",
  "management consultant",
  "it project manager",
  "scrum master",
  "product owner",
  "change manager",
  "cost controller",
  "facility manager",
  "maintenance manager",
  "energy manager",
];

function toTitleCase(value) {
  return value
    .split(" ")
    .filter(Boolean)
    .map((word) => {
      if (word.length <= 3 && word === word.toLowerCase()) {
        return word.toUpperCase();
      }
      return word.charAt(0).toUpperCase() + word.slice(1);
    })
    .join(" ");
}

export const VALID_ROLES = RAW_VALID_ROLES.map(toTitleCase);

export function normalizeValidationValue(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9+#.\s-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function tokenize(value) {
  return normalizeValidationValue(value).split(" ").filter(Boolean);
}

export function isValidRoleSelection(value, roles = VALID_ROLES) {
  const normalizedValue = normalizeValidationValue(value);
  if (!normalizedValue) {
    return false;
  }

  return roles.some((role) => normalizeValidationValue(role) === normalizedValue);
}

export function levenshtein(leftValue, rightValue) {
  const left = normalizeValidationValue(leftValue);
  const right = normalizeValidationValue(rightValue);

  if (!left) {
    return right.length;
  }
  if (!right) {
    return left.length;
  }

  const row = Array.from({ length: right.length + 1 }, (_, index) => index);

  for (let i = 1; i <= left.length; i += 1) {
    let diagonal = row[0];
    row[0] = i;

    for (let j = 1; j <= right.length; j += 1) {
      const cached = row[j];
      const cost = left[i - 1] === right[j - 1] ? 0 : 1;
      row[j] = Math.min(
        row[j] + 1,
        row[j - 1] + 1,
        diagonal + cost
      );
      diagonal = cached;
    }
  }

  return row[right.length];
}

function getAutocompleteScore(input, candidate) {
  const normalizedInput = normalizeValidationValue(input);
  const normalizedCandidate = normalizeValidationValue(candidate);
  const inputTokens = tokenize(normalizedInput);
  const candidateTokens = tokenize(normalizedCandidate);

  let matched = false;
  let score = Number.POSITIVE_INFINITY;

  if (normalizedCandidate.includes(normalizedInput)) {
    matched = true;
    score = 0;
  }

  for (const inputToken of inputTokens) {
    if (inputToken.length < 3) {
      continue;
    }

    for (const candidateToken of candidateTokens) {
      if (candidateToken.includes(inputToken) || inputToken.includes(candidateToken)) {
        matched = true;
        score = Math.min(score, 0.4);
        continue;
      }

      const tokenDistance = levenshtein(inputToken, candidateToken);
      if (tokenDistance <= 2) {
        matched = true;
        score = Math.min(score, tokenDistance + 0.6);
      }
    }
  }

  return {
    matched,
    score,
    role: candidate,
  };
}

export function matchRole(input, roles = VALID_ROLES) {
  const normalizedInput = normalizeValidationValue(input);

  if (normalizedInput.length < 3) {
    return {
      isValid: false,
      matchedRole: "",
      suggestions: [],
      minLengthReached: false,
    };
  }

  const suggestions = roles
    .map((role) => getAutocompleteScore(normalizedInput, role))
    .filter((item) => item.matched)
    .sort((left, right) => left.score - right.score || left.role.localeCompare(right.role));

  return {
    isValid: suggestions.length > 0,
    matchedRole: suggestions[0]?.role || "",
    suggestions: suggestions.slice(0, 5).map((item) => item.role),
    minLengthReached: true,
  };
}
