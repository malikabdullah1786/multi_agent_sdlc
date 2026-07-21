'use client';

import React, { useState } from 'react';
import { ApprovalRequest } from '@/types/chat';
import { useChatStore } from '@/store/chatStore';
import { CheckCircle2, XCircle, MessageSquare, FileText } from 'lucide-react';

interface ApprovalCardProps {
  approval: ApprovalRequest;
}

export function ApprovalCard({ approval }: ApprovalCardProps) {
  const [feedback, setFeedback] = useState('');
  const [showFeedback, setShowFeedback] = useState(false);
  const { submitApproval } = useChatStore();

  const isResolved = approval.status !== 'pending';

  const handleApprove = () => {
    submitApproval(approval.id, true);
  };

  const handleReject = () => {
    if (!showFeedback) {
      setShowFeedback(true);
      return;
    }
    submitApproval(approval.id, false, feedback);
  };

  const typeIcons: Record<string, React.ReactNode> = {
    prd: <FileText size={16} />,
    design: <FileText size={16} />,
    general: <MessageSquare size={16} />,
  };

  return (
    <div className={`approval-card mt-3 animate-slide-in-up ${isResolved ? 'opacity-70' : ''}`}>
      {/* Header */}
      <div className="approval-card-header flex items-center gap-2">
        <span className="text-[var(--state-approval)]">
          {typeIcons[approval.type] || <MessageSquare size={16} />}
        </span>
        <span className="text-sm font-semibold text-[var(--text-primary)]">
          {approval.title}
        </span>
        {isResolved && (
          <span className={`ml-auto text-xs font-medium ${
            approval.status === 'approved' ? 'text-[var(--state-completed)]' : 'text-[var(--state-error)]'
          }`}>
            {approval.status === 'approved' ? '✅ Approved' : '❌ Changes Requested'}
          </span>
        )}
      </div>

      {/* Body */}
      <div className="p-4">
        {approval.message && (
          <p className="text-sm text-[var(--text-secondary)] mb-3">
            {approval.message}
          </p>
        )}

        {approval.questions && approval.questions.length > 0 && (
          <div className="mb-3">
            <p className="text-xs text-[var(--text-muted)] font-medium mb-1 uppercase tracking-wider">
              Questions
            </p>
            <ul className="space-y-1">
              {approval.questions.map((q, i) => (
                <li key={i} className="text-sm text-[var(--text-secondary)] flex items-start gap-2">
                  <span className="text-[var(--state-approval)] mt-0.5">•</span>
                  {q}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Feedback textarea */}
        {showFeedback && !isResolved && (
          <div className="mb-3 animate-slide-in-up">
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="Describe the changes you'd like..."
              className="w-full bg-[var(--bg-primary)] border border-[var(--border-default)] rounded-lg px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-dim)] resize-none focus:outline-none focus:border-[var(--accent-primary)] transition-colors"
              rows={3}
              autoFocus
            />
          </div>
        )}

        {/* Action buttons */}
        {!isResolved && (
          <div className="flex items-center gap-2">
            <button
              onClick={handleApprove}
              className="flex items-center gap-1.5 px-4 py-2 bg-[var(--state-completed)] hover:bg-[var(--state-completed)]/90 text-white text-sm font-medium rounded-lg transition-all hover:shadow-lg hover:shadow-[var(--state-completed)]/20"
            >
              <CheckCircle2 size={14} />
              Approve
            </button>
            <button
              onClick={handleReject}
              className="flex items-center gap-1.5 px-4 py-2 bg-[var(--bg-surface)] hover:bg-[var(--bg-hover)] text-[var(--state-approval)] text-sm font-medium rounded-lg border border-[var(--state-approval)]/30 transition-all"
            >
              <XCircle size={14} />
              {showFeedback ? 'Submit Feedback' : 'Request Changes'}
            </button>
          </div>
        )}

        {/* Show submitted feedback */}
        {isResolved && approval.feedback && (
          <div className="mt-2 p-2 bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-subtle)]">
            <p className="text-xs text-[var(--text-muted)] font-medium mb-1">Feedback:</p>
            <p className="text-sm text-[var(--text-secondary)]">{approval.feedback}</p>
          </div>
        )}
      </div>
    </div>
  );
}
