'use client';

import { useEffect, useRef, useCallback } from 'react';
import { useChatStore } from '@/store/chatStore';
import { useWorkflowStore } from '@/store/workflowStore';

/**
 * Mock WebSocket hook — simulates the real-time connection to the backend.
 * In production, this will connect to FastAPI WebSocket at /ws/workflow/{id}
 * via Redis Pub/Sub for real-time agent state streaming.
 *
 * For now, it provides the same interface but with no real connection.
 */
export function useWebSocket(workflowId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const { setConnected } = useChatStore();

  useEffect(() => {
    // Mark as connected (mock mode)
    setConnected(true);

    return () => {
      setConnected(false);
    };
  }, [workflowId, setConnected]);

  const send = useCallback(
    (data: Record<string, unknown>) => {
      // In production: wsRef.current?.send(JSON.stringify(data))
      console.log('[MockWS] Send:', data);
    },
    []
  );

  const sendApproval = useCallback(
    (approvalId: string, approved: boolean, feedback?: string) => {
      send({
        type: 'approval_response',
        approvalId,
        approved,
        feedback,
      });
    },
    [send]
  );

  const sendUserMessage = useCallback(
    (message: string) => {
      send({
        type: 'user_message',
        content: message,
      });
    },
    [send]
  );

  return {
    isConnected: true,
    send,
    sendApproval,
    sendUserMessage,
  };
}
