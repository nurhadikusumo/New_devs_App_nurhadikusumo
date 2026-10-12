import React, { useEffect, useState } from "react";
import { RevenueSummary } from "./RevenueSummary";
import { SecureAPI } from "../lib/secureApi";
import { useAuth } from "../contexts/AuthContext.new";

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [properties, setProperties] = useState<Array<{ id: string; name: string }>>([]);
  const [selectedProperty, setSelectedProperty] = useState('');
  const [error, setError] = useState('');
  const [month, setMonth] = useState(3);
  const [year, setYear] = useState(2024);

  useEffect(() => {
    let active = true;
    setProperties([]);
    setSelectedProperty('');
    setError('');
    SecureAPI.getDashboardProperties()
      .then((items) => {
        if (active) {
          setProperties(items);
          setSelectedProperty(items[0]?.id ?? '');
        }
      })
      .catch(() => { if (active) setError('Failed to load properties'); });
    return () => { active = false; };
  }, [user?.id]);

  return (
    <div className="p-4 lg:p-6 min-h-full">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold mb-6 text-gray-900">Property Management Dashboard</h1>

        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 lg:p-6">
          <div className="mb-6">
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4">
              <div>
                <h2 className="text-lg lg:text-xl font-medium text-gray-900 mb-2">Revenue Overview</h2>
                <p className="text-sm lg:text-base text-gray-600">
                  Monthly performance insights for your properties
                </p>
              </div>
              
              {/* Property Selector */}
              <div className="flex flex-col sm:items-end">
                <label className="text-xs font-medium text-gray-700 mb-1">Select Property</label>
                <select
                  value={selectedProperty}
                  onChange={(e) => setSelectedProperty(e.target.value)}
                  className="block w-full sm:w-auto min-w-[200px] px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
                >
                  {properties.map((property) => (
                    <option key={property.id} value={property.id}>
                      {property.name}
                    </option>
                  ))}
                </select>
                <div className="flex gap-2 mt-2">
                  <select aria-label="Month" value={month} onChange={(event) => setMonth(Number(event.target.value))} className="border rounded-md p-2 text-sm">
                    {Array.from({ length: 12 }, (_, index) => <option key={index + 1} value={index + 1}>{new Date(2024, index).toLocaleString('en', { month: 'long' })}</option>)}
                  </select>
                  <input aria-label="Year" type="number" min="1" max="9998" value={year} onChange={(event) => setYear(Number(event.target.value))} className="border rounded-md p-2 text-sm w-24" />
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            {error && <p className="text-red-600">{error}</p>}
            {!error && selectedProperty && <RevenueSummary key={`${selectedProperty}:${year}:${month}`} propertyId={selectedProperty} month={month} year={year} />}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
