const prefix = "[Wizard]";

export const logger = {
  info: (...args: unknown[]) => console.info(prefix, ...args),
  warn: (...args: unknown[]) => console.warn(prefix, ...args),
  error: (...args: unknown[]) => console.error(prefix, ...args)
};

