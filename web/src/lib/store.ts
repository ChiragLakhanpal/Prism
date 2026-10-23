// A small store for state that several components read: create it once, set it from anywhere,
// and read it in a component with useStore, which re-renders when the value changes.
import { useSyncExternalStore } from "react";

export type Store<T> = {
  get(): T;
  set(next: T | ((current: T) => T)): void;
  subscribe(listener: () => void): () => void;
};

export function createStore<T>(initial: T): Store<T> {
  let value = initial;
  const listeners = new Set<() => void>();
  return {
    get: () => value,
    set(next) {
      const updated = typeof next === "function" ? (next as (current: T) => T)(value) : next;
      if (Object.is(updated, value)) return;
      value = updated;
      for (const listener of listeners) listener();
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}

export function useStore<T>(store: Store<T>): T {
  return useSyncExternalStore(store.subscribe, store.get, store.get);
}
