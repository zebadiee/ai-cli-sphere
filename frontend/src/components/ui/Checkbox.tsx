interface CheckboxProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

export function Checkbox({ label, checked, onChange, disabled }: CheckboxProps) {
  return (
    <label className="flex items-center space-x-3 cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
        className="w-4 h-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded disabled:opacity-50"
      />
      <span className={`text-sm ${disabled ? 'text-gray-400' : 'text-gray-700'}`}>
        {label}
      </span>
    </label>
  );
}
