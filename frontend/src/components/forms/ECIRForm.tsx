import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ECIRSchema, type ECIRData } from '../../schemas/eicr-validation';
import { SectionA_Details } from './SectionA_Details';
import { SectionB_Reason } from './SectionB_Reason';
import { SectionC_Installation } from './SectionC_Installation';
import { SectionE_Summary } from './SectionE_Summary';
import { SectionG_Declaration } from './SectionG_Declaration';

const sections = [
  { id: 'a', title: 'Section A: Person Ordering Report', component: SectionA_Details },
  { id: 'b', title: 'Section B: Reason for Report', component: SectionB_Reason },
  { id: 'c', title: 'Section C: Installation Details', component: SectionC_Installation },
  { id: 'e', title: 'Section E: Summary', component: SectionE_Summary },
  { id: 'g', title: 'Section G: Declaration', component: SectionG_Declaration },
];

export function ECIRForm() {
  const [currentSection, setCurrentSection] = useState(0);
  const [reportId, setReportId] = useState('EICR-2026-001');

  const { register, handleSubmit, formState: { errors }, watch, setValue } = useForm<ECIRData>({
    resolver: zodResolver(ECIRSchema),
    defaultValues: {
      report_id: reportId,
      version: '1.0',
      sections: {
        section_a: {
          client_name: '',
          client_address: '',
          purpose_of_report: '',
        },
        section_b: {
          reason: 'periodic_inspection',
        },
        section_c: {
          occupier: '',
          installation_address: '',
          type_of_installation: '',
        },
        section_e: {
          general_condition: '',
          overall_assessment: 'SATISFACTORY',
        },
        section_g: {
          inspector_name: '',
          inspector_position: '',
          date_of_inspection: '',
          signature: '',
        },
      },
    },
  });

  const onSubmit = (data: ECIRData) => {
    console.log('Form submitted:', data);
    alert('EICR form submitted successfully! Check console for data.');
  };

  const CurrentSectionComponent = sections[currentSection].component;

  return (
    <div className="max-w-4xl mx-auto bg-white shadow-lg rounded-lg overflow-hidden">
      {/* Header */}
      <div className="bg-blue-600 text-white p-6">
        <h2 className="text-2xl font-bold">Electrical Installation Condition Report</h2>
        <p className="text-blue-100 mt-2">Report ID: {reportId}</p>
      </div>

      {/* Progress Indicator */}
      <div className="bg-gray-100 px-6 py-4">
        <div className="flex items-center justify-between">
          {sections.map((section, index) => (
            <button
              key={section.id}
              onClick={() => setCurrentSection(index)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                index === currentSection
                  ? 'bg-blue-600 text-white'
                  : index < currentSection
                  ? 'bg-green-500 text-white'
                  : 'bg-gray-300 text-gray-700 hover:bg-gray-400'
              }`}
            >
              {section.id.toUpperCase()}
            </button>
          ))}
        </div>
        <div className="mt-2 text-sm text-gray-600">
          {sections[currentSection].title}
        </div>
      </div>

      {/* Form Content */}
      <form onSubmit={handleSubmit(onSubmit)} className="p-6">
        <CurrentSectionComponent
          register={register}
          errors={errors}
          watch={watch}
          setValue={setValue}
        />

        {/* Navigation Buttons */}
        <div className="mt-8 flex justify-between">
          <button
            type="button"
            onClick={() => setCurrentSection(Math.max(0, currentSection - 1))}
            disabled={currentSection === 0}
            className="px-6 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>

          {currentSection < sections.length - 1 ? (
            <button
              type="button"
              onClick={() => setCurrentSection(Math.min(sections.length - 1, currentSection + 1))}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            >
              Next
            </button>
          ) : (
            <button
              type="submit"
              className="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
            >
              Submit Report
            </button>
          )}
        </div>
      </form>

      {/* Authority Notice */}
      <div className="bg-yellow-50 border-t border-yellow-200 p-4">
        <p className="text-sm text-yellow-800">
          <strong>Authority Notice:</strong> Critical fields (C1/C2/C3/FI codes, SATISFACTORY/UNSATISFACTORY assessment)
          require explicit human assertion. No auto-completion is performed.
        </p>
      </div>
    </div>
  );
}
