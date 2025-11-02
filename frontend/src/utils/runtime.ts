export function resolvePath<T = unknown>(data: Record<string, any> | undefined, path: string | undefined): T | undefined {
  if (!data || !path) return undefined;
  const segments = path.split(".").filter(Boolean);
  let current: any = data;
  for (const segment of segments) {
    if (current == null) return undefined;
    if (Array.isArray(current)) {
      const index = Number(segment);
      if (Number.isNaN(index) || index < 0 || index >= current.length) {
        return undefined;
      }
      current = current[index];
      continue;
    }
    current = (current as Record<string, any>)[segment];
  }
  return current as T;
}

export function renderTemplate(template: string, context: Record<string, any>): string {
  return template.replace(/{{\s*([^}]+)\s*}}/g, (_, expression: string) => {
    const value = evaluateExpression(expression.trim(), context);
    return value == null ? "" : String(value);
  });
}

function evaluateExpression(expression: string, context: Record<string, any>) {
  const [pathPart, ...filters] = expression.split("|").map((part) => part.trim()).filter(Boolean);
  let value = resolvePath(context, pathPart);
  for (const filter of filters) {
    const [name, args] = parseFilter(filter);
    value = applyFilter(name, value, args);
  }
  return value;
}

function parseFilter(filter: string): [string, string[]] {
  const match = filter.match(/^(\w+)(?:\((.*)\))?$/);
  if (!match) {
    return [filter, []];
  }
  const [, name, args] = match;
  if (!args) return [name, []];
  return [name, args.split(",").map((arg) => arg.trim())];
}

function applyFilter(name: string, value: any, args: string[]): any {
  switch (name) {
    case "round": {
      const precision = Number(args[0] ?? 0);
      const numeric = Number(value ?? 0);
      if (Number.isNaN(numeric)) return value;
      return Number(numeric.toFixed(precision));
    }
    case "upper":
      return typeof value === "string" ? value.toUpperCase() : value;
    case "lower":
      return typeof value === "string" ? value.toLowerCase() : value;
    default:
      return value;
  }
}
