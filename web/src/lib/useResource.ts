// 서버 상태 라이브러리를 새로 들이지 않는다. 화면 6개에 필요한 것은 이만큼이다.

import { useCallback, useEffect, useState } from "react";

import { ApiError } from "./api";

export interface Resource<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  errorStatus: number | null;
  reload: () => void;
}

export function useResource<T>(load: () => Promise<T>, deps: unknown[]): Resource<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [nonce, setNonce] = useState(0);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(load, deps);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    setErrorStatus(null);
    run()
      .then((value) => {
        if (alive) setData(value);
      })
      .catch((err: unknown) => {
        if (!alive) return;
        if (err instanceof ApiError) {
          setError(err.message);
          setErrorStatus(err.status);
        } else {
          setError("요청 처리 중 오류가 발생했습니다.");
          setErrorStatus(null);
        }
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [run, nonce]);

  return { data, loading, error, errorStatus, reload: () => setNonce((n) => n + 1) };
}
