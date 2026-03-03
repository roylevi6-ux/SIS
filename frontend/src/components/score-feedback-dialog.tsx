'use client';

import { useState } from 'react';
import { useAuth } from '@/lib/auth';
import { useSubmitFeedback } from '@/lib/hooks/use-feedback';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Direction = 'too_high' | 'too_low';

const REASON_OPTIONS: Array<{ value: string; label: string }> = [
  { value: 'off_channel', label: 'Off-channel activity' },
  { value: 'stakeholder_context', label: 'Stakeholder context' },
  { value: 'stage_mismatch', label: 'Stage mismatch' },
  { value: 'score_too_high', label: 'Score too high' },
  { value: 'recent_change', label: 'Recent change' },
  { value: 'other', label: 'Other' },
];

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ScoreFeedbackDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  accountId: string;
  assessmentId: string;
  currentHealthScore: number;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ScoreFeedbackDialog({
  open,
  onOpenChange,
  accountId,
  assessmentId,
  currentHealthScore,
}: ScoreFeedbackDialogProps) {
  const { user } = useAuth();
  const { mutate: submitFeedback, isPending } = useSubmitFeedback();

  const [direction, setDirection] = useState<Direction | ''>('');
  const [reason, setReason] = useState('');
  const [offChannel, setOffChannel] = useState(false);
  const [freeText, setFreeText] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  function resetForm() {
    setDirection('');
    setReason('');
    setOffChannel(false);
    setFreeText('');
    setSuccessMessage('');
    setErrorMessage('');
  }

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen) resetForm();
    onOpenChange(nextOpen);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErrorMessage('');

    if (!direction) {
      setErrorMessage('Please select whether the score is too high or too low.');
      return;
    }
    if (!reason) {
      setErrorMessage('Please select a reason.');
      return;
    }

    submitFeedback(
      {
        account_id: accountId,
        assessment_id: assessmentId,
        author: user?.username ?? 'unknown',
        direction: direction as Direction,
        reason,
        free_text: freeText.trim() || undefined,
        off_channel: offChannel,
      },
      {
        onSuccess: () => {
          setSuccessMessage('Feedback submitted. Thank you.');
          // Close after a short pause so the user sees the confirmation.
          setTimeout(() => handleOpenChange(false), 1200);
        },
        onError: () => {
          setErrorMessage('Something went wrong. Please try again.');
        },
      }
    );
  }

  const isSubmitDisabled = isPending || !direction || !reason;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Give Feedback on Score</DialogTitle>
          <DialogDescription>
            Current health score:{' '}
            <span className="font-semibold text-foreground">{currentHealthScore}</span>
            . Help us calibrate by telling us what seems off.
          </DialogDescription>
        </DialogHeader>

        {successMessage ? (
          <div className="py-6 text-center">
            <p className="text-sm font-medium text-emerald-600 dark:text-emerald-400">
              {successMessage}
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Direction — radio group rendered as styled buttons */}
            <div className="space-y-2">
              <label className="text-sm font-medium leading-none">Direction</label>
              <div className="flex gap-3">
                {(
                  [
                    { value: 'too_high', label: 'Score is too high' },
                    { value: 'too_low', label: 'Score is too low' },
                  ] as const
                ).map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setDirection(opt.value)}
                    className={[
                      'flex-1 rounded-md border px-3 py-2 text-sm font-medium transition-colors',
                      'min-h-[44px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                      direction === opt.value
                        ? 'border-primary bg-primary text-primary-foreground'
                        : 'border-input bg-background hover:bg-muted',
                    ].join(' ')}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Reason */}
            <div className="space-y-2">
              <label htmlFor="feedback-reason" className="text-sm font-medium leading-none">
                Reason
              </label>
              <Select value={reason} onValueChange={setReason}>
                <SelectTrigger id="feedback-reason" className="w-full">
                  <SelectValue placeholder="Select a reason..." />
                </SelectTrigger>
                <SelectContent>
                  {REASON_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Off-channel checkbox */}
            <div className="flex items-start gap-3">
              <input
                id="off-channel"
                type="checkbox"
                checked={offChannel}
                onChange={(e) => setOffChannel(e.target.checked)}
                className="mt-0.5 size-4 shrink-0 cursor-pointer rounded border-input accent-primary"
              />
              <label
                htmlFor="off-channel"
                className="cursor-pointer text-sm font-medium leading-snug"
              >
                There is off-channel activity not captured in calls
              </label>
            </div>

            {/* Free text */}
            <div className="space-y-2">
              <label htmlFor="feedback-notes" className="text-sm font-medium leading-none">
                Additional notes{' '}
                <span className="text-muted-foreground font-normal">(optional)</span>
              </label>
              <Textarea
                id="feedback-notes"
                placeholder="Add any context that would help calibrate the score..."
                value={freeText}
                onChange={(e) => setFreeText(e.target.value)}
                rows={3}
                className="resize-none"
              />
            </div>

            {/* Error */}
            {errorMessage && (
              <p className="text-sm text-destructive">{errorMessage}</p>
            )}

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => handleOpenChange(false)}
                disabled={isPending}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitDisabled}>
                {isPending ? 'Submitting...' : 'Submit Feedback'}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
