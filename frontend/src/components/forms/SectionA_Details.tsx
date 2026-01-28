import { UseFormRegister, FieldErrors, UseFormWatch, UseFormSetValue } from 'react-hook-form';
import { ECIRData } from '../../schemas/eicr-validation';
import { FormField } from '../ui/FormField';

interface Props {
  register: UseFormRegister<ECIRData>;
  errors: FieldErrors<ECIRData>;
  watch: UseFormWatch<ECIRData>;
  setValue: UseFormSetValue<ECIRData>;
}

export function SectionA_Details({ register, errors }: Props) {
  return (
    <div className="space-y-6">
      <h3 className="text-xl font-bold text-gray-800 mb-4">
        Section A: Details of the Person Ordering the Report
      </h3>

      <FormField
        label="Client Name"
        required
        error={errors.sections?.section_a?.client_name?.message}
      >
        <input
          type="text"
          {...register('sections.section_a.client_name')}
          className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="Enter client name"
        />
      </FormField>

      <FormField
        label="Client Address"
        required
        error={errors.sections?.section_a?.client_address?.message}
      >
        <textarea
          {...register('sections.section_a.client_address')}
          className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="Enter client address"
          rows={3}
        />
      </FormField>

      <FormField
        label="Purpose of Report"
        required
        error={errors.sections?.section_a?.purpose_of_report?.message}
      >
        <input
          type="text"
          {...register('sections.section_a.purpose_of_report')}
          className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="e.g., Periodic inspection, Change of occupancy"
        />
      </FormField>
    </div>
  );
}
