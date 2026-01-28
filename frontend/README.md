# ECIR Studio Frontend

React-based user interface for the Electrical Installation Condition Report (ECIR) system.

## Features

- **Form Components**: Complete form interface for all EICR sections (A-K)
- **Validation**: Client-side validation matching ECIR schema
- **Auto-save**: Draft persistence for work-in-progress reports
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Accessibility**: WCAG 2.1 AA compliant
- **Type Safety**: Full TypeScript support

## Getting Started

### Prerequisites

- Node.js 18+ and npm

### Installation

```bash
cd frontend
npm install
```

### Development

Start the development server:

```bash
npm run dev
```

The application will be available at `http://localhost:5173`

### Building

Build for production:

```bash
npm run build
```

The built files will be in the `dist` directory.

### Preview Production Build

```bash
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── forms/          # ECIR form sections (A-K)
│   │   └── ui/             # Reusable UI components
│   ├── hooks/              # Custom React hooks
│   ├── schemas/            # Validation schemas
│   ├── utils/              # Utility functions
│   ├── App.tsx             # Main application component
│   └── main.tsx            # Application entry point
├── public/                 # Static assets
├── package.json
├── tsconfig.json           # TypeScript configuration
├── vite.config.ts          # Vite configuration
└── tailwind.config.js      # Tailwind CSS configuration
```

## Form Sections

The application implements all EICR sections:

- **Section A**: Details of the person ordering the report
- **Section B**: Reason for producing this report
- **Section C**: Details of the installation
- **Section D**: Extent and limitations of the inspection
- **Section E**: Summary of the condition of the installation
- **Section F**: Recommendations
- **Section G**: Declaration
- **Section H**: Schedule of items inspected
- **Section I**: Supply characteristics and earthing arrangements
- **Section J**: Particulars of the installation
- **Section K**: Observations and recommendations

Additional schedules:
- **Circuit Details**: Schedule of circuit details
- **Test Results**: Schedule of test results
- **Inspection Schedule**: Condition report inspection checklist

## Authority Boundaries

The UI enforces the following authority boundaries:

- ❌ NO auto-fill of C1/C2/C3/FI codes
- ❌ NO auto-selection of "SATISFACTORY/UNSATISFACTORY"
- ❌ NO AI-written observations (free-text only)
- ✅ All critical fields require explicit human input
- ✅ Evidence referenced by ID only (not embedded)

## Technologies

- **React 18**: UI framework
- **TypeScript**: Type safety
- **Vite**: Build tool and dev server
- **React Hook Form**: Form state management
- **Zod**: Schema validation
- **Tailwind CSS**: Styling
- **Axios**: HTTP client

## License

See main project LICENSE file.
