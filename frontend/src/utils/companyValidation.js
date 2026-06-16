import { levenshtein, normalizeValidationValue } from "./roleValidation";

function tokenize(value) {
  return normalizeValidationValue(value).split(" ").filter(Boolean);
}

function getCompanyScore(input, company) {
  const normalizedInput = normalizeValidationValue(input);
  const normalizedCompany = normalizeValidationValue(company);
  const inputTokens = tokenize(normalizedInput);
  const companyTokens = tokenize(normalizedCompany);

  let matched = false;
  let score = Number.POSITIVE_INFINITY;

  if (normalizedCompany.includes(normalizedInput) || normalizedInput.includes(normalizedCompany)) {
    matched = true;
    score = 0;
  }

  for (const inputToken of inputTokens) {
    if (inputToken.length < 2) {
      continue;
    }

    for (const companyToken of companyTokens) {
      if (companyToken.includes(inputToken) || inputToken.includes(companyToken)) {
        matched = true;
        score = Math.min(score, 0.4);
        continue;
      }

      const tokenDistance = levenshtein(inputToken, companyToken);
      if (tokenDistance <= 2) {
        matched = true;
        score = Math.min(score, tokenDistance + 0.6);
      }
    }
  }

  return {
    matched,
    score,
    company,
  };
}

export function matchCompany(input, companies) {
  const normalizedInput = normalizeValidationValue(input);

  if (normalizedInput.length < 2) {
    return {
      isValid: false,
      matchedCompany: "",
      suggestions: [],
      minLengthReached: false,
    };
  }

  const suggestions = companies
    .map((company) => getCompanyScore(normalizedInput, company))
    .filter((item) => item.matched)
    .sort((left, right) => left.score - right.score || left.company.localeCompare(right.company));

  return {
    isValid: suggestions.length > 0,
    matchedCompany: suggestions[0]?.company || "",
    suggestions: suggestions.slice(0, 5).map((item) => item.company),
    minLengthReached: true,
  };
}
