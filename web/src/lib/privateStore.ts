/** Browser-private data scope follows the identity adopted by the auth store. */
let owner: string | null = null;

export function setPrivateOwner(value: string | null): void {
  owner = value && value.length > 0 ? value : null;
}
export function privateOwner(): string | null {
  return owner;
}
export function privateStorageKey(prefix: string): string | null {
  return owner === null ? null : `${prefix}.${encodeURIComponent(owner)}`;
}
