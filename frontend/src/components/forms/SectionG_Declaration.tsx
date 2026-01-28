import { UseFormRegister, FieldErrors, UseFormWatch, UseFormSetValue } from 'react-hook-form';
import { ECIRData } from '../../schemas/eicr-validation';
import { FormField } from '../ui/FormField';

interface Props {
  register: UseFormRegister<ECIRData>;
  errors: FieldErrors<ECIRData>;
  watch: UseFormWatch<ECIRData>;
  setValue: UseFormSetValue<ECIRData>;
}

export function SectionG_Declaration({ register, errors }: Props) {
  return (
    <div className="space-y-6">
      <h3 className="text-xl font-bold text-gray-800 mb-4">
        Section G: Declaration
      </h3>

      <div className="bg-blue-50 border border-blue-200 rounded-md p-4 mb-6">
        <p className="text-sm text-blue-800">
          I/We certify that the installation has been inspected and tested and that the results
          are recorded in this report.
        </p>
      </div>

      <FormField
        label="Inspector Name"
        required
        error={errors.sections?.section_g?.inspector_name?.message}
      >
        <input
          type="text"
          {...register('sections.section_g.inspector_name')}
          className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="Enter inspector name"
        />
      </FormField>

      <FormField
        label="Position/Qualification"
        required
        error={errors.sections?.section_g?.inspector_position?.message}
      >
        <input
          type="text"
          {...register('sections.section_g.inspector_position')}
          className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder="e.g., Qualified Electrician, Electrical Engineer"
        />
      </FormField>

      <FormField
        label="Date of Inspection"
        required
        error={errors.sections?.section_g?.date_of_inspection?.message}
      >
        <input
          type="date"
          {...register('sections.section_g.date_of_inspection')}
          className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </FormField>

      <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
        <FormField
          label="Signature (Digital)"
          required
          error={errors.sections?.section_g?.signature?.message}
        >
          <input
            type="text"
            {...register('sections.section_g.signature')}
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="Type your name to sign digitally"
          />
          <p className="text-xs text-yellow-700 mt-1">
            ⚠️ By typing your name, you are digitally signing this report and certifying its accuracy.
          </p>
        </FormField>
      </div>

      <FormField
        label="Next Inspection Recommended"
        error={errors.sections?.section_g?.next_inspection_date?.message}
      >
        <input
          type="date"
          {...register('sections.section_g.next_inspection_date')}
          className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </FormField>
    </div>
  );
}
