import { UseFormRegister } from 'react-hook-form';

interface RadioOption {
  value: string;
  label: string;
}

interface RadioGroupProps {
  label: string;
  name: string;
  options: RadioOption[];
  register: UseFormRegister<any>;
  required?: boolean;
  error?: string;
}

export function RadioGroup({ label, name, options, register, required, error }: RadioGroupProps) {
  return (
    <div className="radio-group">
      <label className="block text-sm font-medium text-gray-700 mb-3">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      <div className="space-y-2">
        {options.map((option) => (
          <label key={option.value} className="flex items-center space-x-3 cursor-pointer">
            <input
              type="radio"
              value={option.value}
              {...register(name)}
              className="w-4 h-4 text-blue-600 focus:ring-blue-500 border-gray-300"
            />
            <span className="text-sm text-gray-700">{option.label}</span>
          </label>
        ))}
      </div>
      {error && (
        <p className="mt-1 text-sm text-red-600">{error}</p>
      )}
    </div>
  );
}
