import { UseFormRegister, FieldErrors, UseFormWatch, UseFormSetValue } from 'react-hook-form';
import { ECIRData } from '../../schemas/eicr-validation';
import { FormField } from '../ui/FormField';

interface Props {
  register: UseFormRegister<ECIRData>;
  errors: FieldErrors<ECIRData>;
  watch: UseFormWatch<ECIRData>;
  setValue: UseFormSetValue<ECIRData>;
}

export function SectionC_Installation({ register, errors }: Props) {
  return (
    <div className="space-y-6">
      <h3 className="text-xl font-bold text-gray-800 mb-4">
        Section C: Details of the Installation
      </h3>

      <FormField
        label="Occupier"
        required
        error={errors.sections?.section_c?.occupier?.message}
      >
        <input
          type="text"
          {...register('sections.section_c.occupier')}
          className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="Enter occupier name"
        />
      </FormField>

      <FormField
        label="Installation Address"
        required
        error={errors.sections?.section_c?.installation_address?.message}
      >
        <textarea
          {...register('sections.section_c.installation_address')}
          className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="Enter installation address"
          rows={3}
        />
      </FormField>

      <FormField
        label="Type of Installation"
        required
        error={errors.sections?.section_c?.type_of_installation?.message}
      >
        <input
          type="text"
          {...register('sections.section_c.type_of_installation')}
          className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="e.g., Domestic, Commercial, Industrial"
        />
      </FormField>

      <FormField
        label="Estimated Age of Installation"
        error={errors.sections?.section_c?.estimated_age?.message}
      >
        <input
          type="text"
          {...register('sections.section_c.estimated_age')}
          className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="e.g., 10 years, Unknown"
        />
      </FormField>
    </div>
  );
}
