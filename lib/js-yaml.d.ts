declare module "js-yaml" {
  export function dump(value: unknown, options?: {
    noRefs?: boolean;
    lineWidth?: number;
  }): string;
}
