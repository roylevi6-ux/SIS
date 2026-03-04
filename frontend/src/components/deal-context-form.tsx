'use client';

import { useState, useEffect } from 'react';
import { usePermissions } from '@/lib/permissions';
import {
  useDealContext,
  useDealContextQuestions,
  useSubmitDealContext,
} from '@/lib/hooks/use-deal-context';
import type { DealContextQuestion } from '@/lib/api-types';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface DealContextFormProps {
  accountId: string;
  onAnalysisRequest?: () => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STALENESS_DAYS = 60;

function isStale(createdAt: string): boolean {
  const age = (Date.now() - new Date(createdAt).getTime()) / (1000 * 60 * 60 * 24);
  return age > STALENESS_DAYS;
}

function formatRelativeDate(dateStr: string): string {
  const d = new Date(dateStr);
  const days = Math.floor((Date.now() - d.getTime()) / (1000 * 60 * 60 * 24));
  if (days === 0) return 'today';
  if (days === 1) return 'yesterday';
  if (days < 30) return `${days} days ago`;
  const months = Math.floor(days / 30);
  return months === 1 ? '1 month ago' : `${months} months ago`;
}

// ---------------------------------------------------------------------------
// Individual question input renderers
// ---------------------------------------------------------------------------

function TextInput({
  value,
  onChange,
  maxChars,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  maxChars?: number;
  placeholder?: string;
}) {
  return (
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      maxLength={maxChars}
      placeholder={placeholder ?? 'Enter your response...'}
      rows={3}
      className="w-full rounded-md border border-border bg-muted px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-none min-h-[44px]"
    />
  );
}

function DropdownInput({
  value,
  onChange,
  options,
}: {
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-md border border-border bg-muted px-3 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring min-h-[44px] appearance-none"
    >
      <option value="">-- Select --</option>
      {options.map((opt) => (
        <option key={opt} value={opt}>
          {opt}
        </option>
      ))}
    </select>
  );
}

function DropdownTextInput({
  value,
  onChange,
  options,
  maxChars,
}: {
  value: string;
  onChange: (v: string) => void;
  options: string[];
  maxChars?: number;
}) {
  // Stored as "OPTION|||elaboration text"
  const parts = value.split('|||');
  const dropdownVal = parts[0] ?? '';
  const textVal = parts[1] ?? '';

  const update = (drop: string, text: string) => {
    onChange(`${drop}|||${text}`);
  };

  return (
    <div className="space-y-2">
      <select
        value={dropdownVal}
        onChange={(e) => update(e.target.value, textVal)}
        className="w-full rounded-md border border-border bg-muted px-3 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring min-h-[44px] appearance-none"
      >
        <option value="">-- Select --</option>
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
      {dropdownVal && (
        <textarea
          value={textVal}
          onChange={(e) => update(dropdownVal, e.target.value)}
          maxLength={maxChars}
          placeholder="Add elaboration..."
          rows={2}
          className="w-full rounded-md border border-border bg-muted px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-none"
        />
      )}
    </div>
  );
}

function MultiCategoryTextInput({
  value,
  onChange,
  changeCategories,
  maxChars,
}: {
  value: string;
  onChange: (v: string) => void;
  changeCategories: string[];
  maxChars?: number;
}) {
  // Stored as "CAT1,CAT2|||elaboration text"
  const parts = value.split('|||');
  const selectedCats = parts[0] ? parts[0].split(',').filter(Boolean) : [];
  const textVal = parts[1] ?? '';

  const toggleCat = (cat: string) => {
    const next = selectedCats.includes(cat)
      ? selectedCats.filter((c) => c !== cat)
      : [...selectedCats, cat];
    onChange(`${next.join(',')}|||${textVal}`);
  };

  const updateText = (text: string) => {
    onChange(`${selectedCats.join(',')}|||${text}`);
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {changeCategories.map((cat) => {
          const selected = selectedCats.includes(cat);
          return (
            <button
              key={cat}
              type="button"
              onClick={() => toggleCat(cat)}
              className={`min-h-[44px] px-3 py-1.5 rounded-md border text-sm transition-colors ${
                selected
                  ? 'border-brand-500 bg-brand-500/15 text-brand-400'
                  : 'border-border bg-muted text-muted-foreground hover:border-brand-500/50'
              }`}
            >
              {cat}
            </button>
          );
        })}
      </div>
      {selectedCats.length > 0 && (
        <textarea
          value={textVal}
          onChange={(e) => updateText(e.target.value)}
          maxLength={maxChars}
          placeholder="Describe the changes..."
          rows={2}
          className="w-full rounded-md border border-border bg-muted px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-none"
        />
      )}
    </div>
  );
}

function ScaleTextInput({
  value,
  onChange,
  scaleMin = 1,
  scaleMax = 5,
  maxChars,
}: {
  value: string;
  onChange: (v: string) => void;
  scaleMin?: number;
  scaleMax?: number;
  maxChars?: number;
}) {
  // Stored as "SCALE|||explanation"
  const parts = value.split('|||');
  const scaleVal = parts[0] ?? '';
  const textVal = parts[1] ?? '';

  const update = (scale: string, text: string) => {
    onChange(`${scale}|||${text}`);
  };

  const scaleNumbers = Array.from(
    { length: scaleMax - scaleMin + 1 },
    (_, i) => String(scaleMin + i),
  );

  return (
    <div className="space-y-3">
      <div className="flex gap-2 flex-wrap">
        {scaleNumbers.map((n) => (
          <button
            key={n}
            type="button"
            onClick={() => update(n, textVal)}
            className={`min-h-[44px] min-w-[44px] rounded-md border text-sm font-medium transition-colors ${
              scaleVal === n
                ? 'border-brand-500 bg-brand-500/15 text-brand-400'
                : 'border-border bg-muted text-muted-foreground hover:border-brand-500/50'
            }`}
          >
            {n}
          </button>
        ))}
      </div>
      {scaleVal && (
        <textarea
          value={textVal}
          onChange={(e) => update(scaleVal, e.target.value)}
          maxLength={maxChars}
          placeholder="Explain your rating..."
          rows={2}
          className="w-full rounded-md border border-border bg-muted px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-none"
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Question item component
// ---------------------------------------------------------------------------

function QuestionItem({
  questionId,
  question,
  value,
  onChange,
  readOnly,
}: {
  questionId: string;
  question: DealContextQuestion;
  value: string;
  onChange: (v: string) => void;
  readOnly: boolean;
}) {
  const hasValue = value.trim().length > 0;

  // Read-only: skip unanswered questions
  if (readOnly && !hasValue) return null;

  // Read-only display formatting
  const renderReadOnlyValue = () => {
    if (!hasValue) return <span className="text-muted-foreground italic">Not answered</span>;

    if (question.input_type === 'dropdown_text') {
      const [drop, text] = value.split('|||');
      return (
        <div className="space-y-1">
          <span className="font-medium">{drop}</span>
          {text && <p className="text-muted-foreground text-sm">{text}</p>}
        </div>
      );
    }

    if (question.input_type === 'multi_category_text') {
      const [cats, text] = value.split('|||');
      const catList = cats ? cats.split(',').filter(Boolean) : [];
      return (
        <div className="space-y-1">
          <div className="flex flex-wrap gap-1.5">
            {catList.map((c) => (
              <span
                key={c}
                className="px-2 py-0.5 rounded text-xs border border-brand-500/40 bg-brand-500/10 text-brand-400"
              >
                {c}
              </span>
            ))}
          </div>
          {text && <p className="text-muted-foreground text-sm">{text}</p>}
        </div>
      );
    }

    if (question.input_type === 'scale_text') {
      const [scale, text] = value.split('|||');
      return (
        <div className="space-y-1">
          <span className="font-medium">
            Rating: {scale}/{question.scale_max ?? 5}
          </span>
          {text && <p className="text-muted-foreground text-sm">{text}</p>}
        </div>
      );
    }

    return <p className="text-sm leading-relaxed">{value}</p>;
  };

  return (
    <div className="space-y-2">
      <div className="flex items-start justify-between gap-2">
        <label className="text-sm font-medium leading-snug">
          {question.label}
        </label>
        <span className="text-xs text-muted-foreground shrink-0 mt-0.5">{question.category}</span>
      </div>

      {readOnly ? (
        <div className="text-sm">{renderReadOnlyValue()}</div>
      ) : (
        <>
          {question.input_type === 'text' && (
            <TextInput
              value={value}
              onChange={onChange}
              maxChars={question.max_chars}
            />
          )}
          {question.input_type === 'dropdown' && (
            <DropdownInput
              value={value}
              onChange={onChange}
              options={question.options ?? []}
            />
          )}
          {question.input_type === 'dropdown_text' && (
            <DropdownTextInput
              value={value}
              onChange={onChange}
              options={question.options ?? []}
              maxChars={question.max_chars}
            />
          )}
          {question.input_type === 'multi_category_text' && (
            <MultiCategoryTextInput
              value={value}
              onChange={onChange}
              changeCategories={question.change_categories ?? []}
              maxChars={question.max_chars}
            />
          )}
          {question.input_type === 'scale_text' && (
            <ScaleTextInput
              value={value}
              onChange={onChange}
              scaleMin={question.scale_min}
              scaleMax={question.scale_max}
              maxChars={question.max_chars}
            />
          )}
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function FormSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="space-y-2">
          <div className="h-4 w-48 rounded bg-muted" />
          <div className="h-20 rounded bg-muted/60" />
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Success toast / prompt
// ---------------------------------------------------------------------------

function SuccessBanner({ onAnalysisRequest }: { onAnalysisRequest?: () => void }) {
  return (
    <div className="rounded-md border border-brand-500/40 bg-brand-500/10 px-4 py-3 flex items-center justify-between gap-3">
      <p className="text-sm text-brand-400 font-medium">Context saved.</p>
      {onAnalysisRequest && (
        <button
          type="button"
          onClick={onAnalysisRequest}
          className="text-xs font-medium text-brand-400 underline underline-offset-2 hover:opacity-80 transition-opacity shrink-0"
        >
          Run analysis now?
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function DealContextForm({ accountId, onAnalysisRequest }: DealContextFormProps) {
  const { isTlOrAbove } = usePermissions();
  const [isEditing, setIsEditing] = useState(false);
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [showSuccess, setShowSuccess] = useState(false);

  const {
    data: contextData,
    isLoading: contextLoading,
  } = useDealContext(accountId);

  const {
    data: questionsData,
    isLoading: questionsLoading,
  } = useDealContextQuestions();

  const { mutate: submitContext, isPending: isSaving } = useSubmitDealContext();

  // Pre-fill form values from current context when data loads
  useEffect(() => {
    if (contextData?.current) {
      const prefilled: Record<string, string> = {};
      Object.entries(contextData.current).forEach(([qid, entry]) => {
        prefilled[qid] = entry.response_text;
      });
      setFormValues(prefilled);
    }
  }, [contextData]);

  const isLoading = contextLoading || questionsLoading;

  // Find oldest entry date for staleness check
  const oldestEntryDate = contextData?.current
    ? Object.values(contextData.current).sort(
        (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
      )[0]?.created_at
    : undefined;

  const contextIsStale = oldestEntryDate ? isStale(oldestEntryDate) : false;

  const hasAnyContext =
    contextData?.current && Object.keys(contextData.current).length > 0;

  const handleSave = () => {
    const entries = Object.entries(formValues)
      .filter(([, text]) => text.trim().length > 0)
      .map(([qid, text]) => ({
        question_id: Number(qid),
        response_text: text.trim(),
      }));

    submitContext(
      { account_id: accountId, entries },
      {
        onSuccess: () => {
          setIsEditing(false);
          setShowSuccess(true);
          setTimeout(() => setShowSuccess(false), 8000);
        },
      },
    );
  };

  const handleCancel = () => {
    // Reset to saved values
    if (contextData?.current) {
      const reset: Record<string, string> = {};
      Object.entries(contextData.current).forEach(([qid, entry]) => {
        reset[qid] = entry.response_text;
      });
      setFormValues(reset);
    } else {
      setFormValues({});
    }
    setIsEditing(false);
  };

  return (
    <div className="rounded-xl border border-border bg-card p-5 space-y-4">
      {/* Header row */}
      <div className="flex items-center justify-between gap-3">
        <div className="space-y-0.5">
          <h3 className="text-base font-semibold">Deal Context</h3>
          {oldestEntryDate && !isEditing && (
            <p className="text-xs text-muted-foreground">
              Last updated {formatRelativeDate(oldestEntryDate)}
            </p>
          )}
        </div>

        {isTlOrAbove && !isEditing && (
          <button
            type="button"
            onClick={() => {
              setShowSuccess(false);
              setIsEditing(true);
            }}
            className="min-h-[44px] px-4 py-2 rounded-md border border-border bg-muted text-sm font-medium text-foreground hover:border-brand-500/60 hover:bg-brand-500/5 transition-colors"
          >
            {hasAnyContext ? 'Edit' : 'Add Context'}
          </button>
        )}
      </div>

      {/* Staleness banner */}
      {contextIsStale && !isEditing && (
        <div className="rounded-md border border-neutral/40 bg-neutral-bg px-4 py-2.5 flex items-center gap-2">
          <span className="text-neutral text-sm">
            Context is over {STALENESS_DAYS} days old — consider updating before next analysis.
          </span>
        </div>
      )}

      {/* Success banner */}
      {showSuccess && (
        <SuccessBanner onAnalysisRequest={onAnalysisRequest} />
      )}

      {/* Body */}
      {isLoading ? (
        <FormSkeleton />
      ) : !questionsData ? (
        <p className="text-sm text-muted-foreground">
          Unable to load questions. Check backend connectivity.
        </p>
      ) : (
        <div className="space-y-6">
          {Object.entries(questionsData).map(([qid, question]) => (
            <QuestionItem
              key={qid}
              questionId={qid}
              question={question}
              value={formValues[qid] ?? ''}
              onChange={(v) =>
                setFormValues((prev) => ({ ...prev, [qid]: v }))
              }
              readOnly={!isEditing}
            />
          ))}

          {!isEditing && !hasAnyContext && (
            <p className="text-sm text-muted-foreground py-2">
              No deal context has been entered yet.
              {isTlOrAbove && ' Click "Add Context" to fill in guided questions.'}
            </p>
          )}
        </div>
      )}

      {/* Edit mode actions */}
      {isEditing && (
        <div className="flex items-center gap-3 pt-2 border-t border-border">
          <button
            type="button"
            onClick={handleSave}
            disabled={isSaving}
            className="min-h-[44px] px-5 py-2 rounded-md bg-brand-500 text-primary-foreground text-sm font-medium hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isSaving ? 'Saving...' : 'Save Context'}
          </button>
          <button
            type="button"
            onClick={handleCancel}
            disabled={isSaving}
            className="min-h-[44px] px-4 py-2 rounded-md border border-border bg-muted text-sm font-medium text-foreground hover:border-brand-500/50 disabled:opacity-50 transition-colors"
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}
