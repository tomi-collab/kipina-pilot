interface VibeControlsProps {
  promptText: string
  placeholder: string
  updateLabel: string
  updatingLabel: string
  isLoading: boolean
  onPromptChange: (value: string) => void
  onSubmit: () => void
}

export function VibeControls({
  promptText,
  placeholder,
  updateLabel,
  updatingLabel,
  isLoading,
  onPromptChange,
  onSubmit,
}: VibeControlsProps) {
  return (
    <div>
      <textarea
        className="h-24 w-full resize-none rounded-2xl border border-slate-700 bg-slate-800 p-4 text-base text-slate-100 outline-none transition-all placeholder:text-slate-500 focus:border-transparent focus:ring-2 focus:ring-emerald-500 md:h-32"
        placeholder={placeholder}
        value={promptText}
        onChange={(event) => onPromptChange(event.target.value)}
        disabled={isLoading}
        aria-label={placeholder}
      />
      <button
        type="button"
        className="mt-4 min-h-14 w-full rounded-2xl bg-emerald-500 px-6 py-4 text-lg font-bold text-slate-950 shadow-[0_0_20px_rgba(16,185,129,0.3)] transition-all hover:bg-emerald-400 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50"
        onClick={onSubmit}
        disabled={isLoading || !promptText.trim()}
      >
        {isLoading ? updatingLabel : updateLabel}
      </button>
    </div>
  )
}
