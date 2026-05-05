"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { AgentRunResponse } from "@/lib/api";
import { Check, X } from "lucide-react";

interface Props {
  run: AgentRunResponse | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDecision: (decision: "approved" | "rejected", gatedActions: string[]) => void | Promise<void>;
}

export function ApprovalModal({ run, open, onOpenChange, onDecision }: Props) {
  const compliance = run?.outputs.find((output) => output.agent_name === "compliance");
  const actions = compliance?.result.gated_actions;
  const gatedActions = Array.isArray(actions) ? actions.map(String) : [];

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/70" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[min(92vw,560px)] -translate-x-1/2 -translate-y-1/2 rounded-lg border border-gray-800 bg-gray-950 p-6 shadow-2xl">
          <Dialog.Title className="text-lg font-semibold text-white">Human Approval Required</Dialog.Title>
          <Dialog.Description className="mt-2 text-sm text-gray-400">
            Compliance blocked one or more high-impact actions for event {run?.event_id.slice(0, 8)}.
          </Dialog.Description>

          <div className="mt-5 space-y-2">
            {gatedActions.length ? gatedActions.map((action, index) => (
              <div key={index} className="rounded-md border border-red-900/50 bg-red-950/20 p-3 text-sm text-red-100">
                {action}
              </div>
            )) : (
              <div className="rounded-md border border-gray-800 bg-gray-900 p-3 text-sm text-gray-400">
                No gated action details were returned.
              </div>
            )}
          </div>

          <div className="mt-6 flex justify-end gap-3">
            <button
              type="button"
              onClick={() => onDecision("rejected", gatedActions)}
              className="inline-flex items-center gap-2 rounded-md border border-gray-700 px-4 py-2 text-sm text-gray-200 hover:bg-gray-900"
            >
              <X className="h-4 w-4" /> Reject
            </button>
            <button
              type="button"
              onClick={() => onDecision("approved", gatedActions)}
              className="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
            >
              <Check className="h-4 w-4" /> Approve
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
