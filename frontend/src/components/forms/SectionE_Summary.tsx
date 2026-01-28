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

export function SectionE_Summary({ register, errors }: Props) {
  return (
    <div className="space-y-6">
      <h3 className="text-xl font-bold text-gray-800 mb-4">
        Section E: Summary of the Condition of the Installation
      </h3>

      <FormField
        label="General Condition of the Installation (in terms of electrical safety)"
        required
        error={errors.sections?.section_e?.general_condition?.message}
      >
        <textarea
          {...register('sections.section_e.general_condition')}
          className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="Describe the general condition..."
          rows={4}
        />
      </FormField>

      <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
        <p className="text-sm text-yellow-800 font-medium mb-3">
          ⚠️ CRITICAL FIELD - HUMAN ASSERTION REQUIRED
        </p>
        <RadioGroup
          label="Overall Assessment of the Installation (in terms of its suitability for continued use)"
          name="sections.section_e.overall_assessment"
          options={[
            { value: 'SATISFACTORY', label: 'SATISFACTORY' },
            { value: 'UNSATISFACTORY', label: 'UNSATISFACTORY' },
          ]}
          register={register}
          required
          error={errors.sections?.section_e?.overall_assessment?.message}
        />
        <p className="text-xs text-yellow-700 mt-2">
          *An unsatisfactory assessment indicates that dangerous (code C1) and/or potentially dangerous (code C2)
          conditions have been identified. This selection MUST be made by a qualified inspector.
        </p>
      </div>
    </div>
  );
}
