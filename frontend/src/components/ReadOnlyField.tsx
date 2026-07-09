import React from "react";

interface ReadOnlyFieldProps {
  label: string;
  value?: string | null;
}

const ReadOnlyField: React.FC<ReadOnlyFieldProps> = ({ label, value }) => {
  const displayValue = value && value.trim() ? value : "Not detected";

  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 mb-1">
        {label}
      </label>
      <div className="rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-800 min-h-[42px] flex items-center">
        {displayValue}
      </div>
    </div>
  );
};

export default ReadOnlyField;
