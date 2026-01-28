import { UseFormRegister, FieldErrors, UseFormWatch, UseFormSetValue } from 'react-hook-form';
import { ECIRData } from '../../schemas/eicr-validation';
import { FormField } from '../ui/FormField';
import { RadioGroup } from '../ui/RadioGroup';

interface Props {
  register: UseFormRegister<ECIRData>;
  errors: FieldErrors<ECIRData>;
  watch: UseFormWatch<ECIRData>;
  setValue: UseFormSetValue<ECIRData>;
}

export function SectionB_Reason({ register, errors, watch }: Props) {
  const reason = watch('sections.section_b.reason');

  return (
    <div className="space-y-6">
      <h3 className="text-xl font-bold text-gray-800 mb-4">
        Section B: Reason for Producing this Report
      </h3>

      <RadioGroup
        label="Select Reason"
        name="sections.section_b.reason"
        options={[
          { value: 'change_of_occupancy', label: 'Change of occupancy' },
          { value: 'change_of_use', label: 'Change of use' },
          { value: 'periodic_inspection', label: 'Periodic inspection' },
          { value: 'previous_inspection_recommendations', label: 'Previous inspection recommendations' },
          { value: 'other', label: 'Other (specify below)' },
        ]}
        register={register}
        error={errors.sections?.section_b?.reason?.message}
      />

      {reason === 'other' && (
        <FormField
          label="Other Reason (please specify)"
          error={errors.sections?.section_b?.other_reason?.message}
        >
          <input
            type="text"
            {...register('sections.section_b.other_reason')}
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Specify other reason"
          />
        </FormField>
      )}
    </div>
  );
}
