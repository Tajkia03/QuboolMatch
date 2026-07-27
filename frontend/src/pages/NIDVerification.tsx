// src/pages/NIDVerification.tsx
import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import NIDImageDisplay from "../components/NIDImageDisplay";
import { getAccessToken, API_BASE_URL } from "../services/api";

type OcrStatus = "idle" | "processing" | "success" | "failed";

type ExtractedNidInformation = {
  document_detected: boolean;
  name: string | null;
  father_name: string | null;
  mother_name: string | null;
  date_of_birth: string | null;
  nid_number: string | null;
  address: string | null;
  blood_group: string | null;
  image_quality: string | null;
  warnings: string[];
};

type VerificationStatusResponse = {
  verification_status: string;
  admin_review_notes?: string | null;
  verified_at?: string | null;
  verification_notes?: string | null;
  rejection_notes?: string | null;
  ocr_name?: string | null;
  ocr_father_name?: string | null;
  ocr_mother_name?: string | null;
  ocr_date_of_birth?: string | null;
  ocr_nid_number?: string | null;
  ocr_address?: string | null;
  ocr_blood_group?: string | null;
  ocr_image_quality?: string | null;
  ocr_warnings?: string[] | null;
  ocr_confirmed?: boolean;
  ocr_processed_at?: string | null;
  has_nid_image?: boolean;
  nid_image_filename?: string | null;
  has_nid_back_image?: boolean;
  nid_back_image_filename?: string | null;
};

const hasSavedOcrData = (statusData: VerificationStatusResponse) =>
  Boolean(
    statusData.ocr_name ||
      statusData.ocr_father_name ||
      statusData.ocr_mother_name ||
      statusData.ocr_date_of_birth ||
      statusData.ocr_nid_number ||
      statusData.ocr_address ||
      statusData.ocr_blood_group ||
      statusData.ocr_image_quality ||
      (statusData.ocr_warnings && statusData.ocr_warnings.length > 0) ||
      statusData.ocr_processed_at
  );

const NIDVerification: React.FC = () => {
  const ONBOARDING_PENDING_KEY = "verificationOnboardingPending";
  const [file, setFile] = useState<File | null>(null);
  const [backFile, setBackFile] = useState<File | null>(null);
  const [notes, setNotes] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [currentStatus, setCurrentStatus] = useState<VerificationStatusResponse | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
  const [ocrStatus, setOcrStatus] = useState<OcrStatus>("idle");
  const [ocrError, setOcrError] = useState("");
  const [ocrConfirmed, setOcrConfirmed] = useState(false);
  const [ocrData, setOcrData] = useState<ExtractedNidInformation | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const backFileInputRef = useRef<HTMLInputElement | null>(null);
  const navigate = useNavigate();

  const backendVerificationStatus = currentStatus?.verification_status ?? null;
  const isVerificationLocked = backendVerificationStatus === "verified";
  const isBackendStatusVisible = Boolean(
    backendVerificationStatus &&
      ["pending", "verified", "rejected", "resubmission_required", "correction_required", "processing"].includes(backendVerificationStatus)
  );
  const canContinue =
    ocrStatus === "success" &&
    Boolean(ocrData) &&
    ocrConfirmed &&
    backendVerificationStatus !== "pending" &&
    backendVerificationStatus !== "verified" &&
    backendVerificationStatus !== "processing";

  useEffect(() => {
    const fetchVerificationStatus = async () => {
      try {
        const token = getAccessToken();
        if (!token) {
          return;
        }

        const response = await fetch(`${API_BASE_URL}/verification/status`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });

        if (response.ok) {
          const statusData: VerificationStatusResponse = await response.json();
          setCurrentStatus(statusData);

          setNotes(statusData.verification_notes ?? "");
          setOcrConfirmed(Boolean(statusData.ocr_confirmed) || statusData.verification_status === "verified");
          setStatus("");

          if (hasSavedOcrData(statusData)) {
            setOcrData({
              document_detected: true,
              name: statusData.ocr_name ?? null,
              father_name: statusData.ocr_father_name ?? null,
              mother_name: statusData.ocr_mother_name ?? null,
              date_of_birth: statusData.ocr_date_of_birth ?? null,
              nid_number: statusData.ocr_nid_number ?? null,
              address: statusData.ocr_address ?? null,
              blood_group: statusData.ocr_blood_group ?? null,
              image_quality: statusData.ocr_image_quality ?? null,
              warnings: statusData.ocr_warnings ?? [],
            });
            setOcrStatus("success");
          } else {
            setOcrData(null);
            setOcrStatus("idle");
          }

          if (statusData.verification_status === "verified") {
            localStorage.removeItem(ONBOARDING_PENDING_KEY);
          }
        }
      } catch (error) {
        console.error("Error fetching verification status:", error);
      } finally {
        setStatusLoading(false);
      }
    };

    fetchVerificationStatus();
  }, []);

  useEffect(() => {
    if (currentStatus?.verification_status === "verified") {
      localStorage.removeItem(ONBOARDING_PENDING_KEY);
    }
  }, [currentStatus?.verification_status]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (isVerificationLocked) {
      return;
    }
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setOcrStatus("idle");
      setOcrError("");
      setOcrConfirmed(false);
      setOcrData(null);
    }
  };

  const handleBackFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (isVerificationLocked) {
      return;
    }
    if (e.target.files && e.target.files[0]) {
      setBackFile(e.target.files[0]);
      setOcrStatus("idle");
      setOcrError("");
      setOcrConfirmed(false);
      setOcrData(null);
    }
  };

  const extractNidInformation = async () => {
    if (isVerificationLocked || !file || !backFile) {
      return;
    }

    setOcrStatus("processing");
    setOcrError("");
    setOcrConfirmed(false);
    setOcrData(null);

    try {
      const token = getAccessToken();
      if (!token) {
        throw new Error("You must be logged in to extract NID information");
      }

      const formData = new FormData();
      formData.append("nid_image", file);
      formData.append("nid_back_image", backFile);

      const response = await fetch(`${API_BASE_URL}/verification/extract-nid`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await response.json().catch(() => null);

      if (!response.ok || !data?.success) {
        throw new Error(
          data?.message ||
            data?.detail ||
            "We could not read the NID image. Please upload a clearer image and try again."
        );
      }

      setOcrData({
        document_detected: Boolean(data.document_detected),
        name: data.name ?? null,
        father_name: data.father_name ?? null,
        mother_name: data.mother_name ?? null,
        date_of_birth: data.date_of_birth ?? null,
        nid_number: data.nid_number ?? null,
        address: data.address ?? null,
        blood_group: data.blood_group ?? null,
        image_quality: data.image_quality ?? null,
        warnings: Array.isArray(data.warnings) ? data.warnings : [],
      });
      setOcrStatus("success");
    } catch (err) {
      console.error("OCR extraction error:", err);
      setOcrStatus("failed");
      setOcrError(err instanceof Error ? err.message : "We could not read the NID image. Please upload a clearer image and try again.");
      setOcrData(null);
    }
  };

  const handleExtractClick = async () => {
    try {
      await extractNidInformation();
    } catch (err) {
      console.error("Unexpected OCR extraction error:", err);
      setOcrStatus("failed");
      setOcrError("We could not read the NID image. Please upload a clearer image and try again.");
      setOcrData(null);
    }
  };

  const handleUploadDifferentImage = () => {
    if (isVerificationLocked) {
      return;
    }
    setFile(null);
    setBackFile(null);
    setOcrStatus("idle");
    setOcrError("");
    setOcrConfirmed(false);
    setOcrData(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    if (backFileInputRef.current) {
      backFileInputRef.current.value = "";
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setStatus("Submitting...");

    try {
      if (!file) {
        throw new Error("Please select the front side of your NID");
      }

      if (!backFile) {
        throw new Error("Please select the back side of your NID");
      }

      const formData = new FormData();
      formData.append("nid_image", file);
      formData.append("nid_back_image", backFile);
      if (ocrData) {
        formData.append("ocr_name", ocrData.name ?? "");
        formData.append("ocr_father_name", ocrData.father_name ?? "");
        formData.append("ocr_mother_name", ocrData.mother_name ?? "");
        formData.append("ocr_date_of_birth", ocrData.date_of_birth ?? "");
        formData.append("ocr_nid_number", ocrData.nid_number ?? "");
        formData.append("ocr_address", ocrData.address ?? "");
        formData.append("ocr_blood_group", ocrData.blood_group ?? "");
      }
      if (notes.trim()) {
        formData.append("verification_notes", notes);
      }

      const token = getAccessToken();
      if (!token) {
        throw new Error("You must be logged in to submit verification");
      }

      const response = await fetch(`${API_BASE_URL}/verification/submit`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to submit verification");
      }

      const data = await response.json();

      if (data.success) {
        const statusResponse = await fetch(`${API_BASE_URL}/verification/status`, {
          headers: {
            "Authorization": `Bearer ${token}`
          }
        });
        if (statusResponse.ok) {
          const statusData: VerificationStatusResponse = await statusResponse.json();
          setCurrentStatus(statusData);
          setNotes(statusData.verification_notes ?? "");
          setOcrConfirmed(Boolean(statusData.ocr_confirmed) || statusData.verification_status === "verified");
        }
        setStatus("");
      } else {
        throw new Error(data.message || "Verification submission failed");
      }

    } catch (err) {
      console.error("Verification submission error:", err);
      setError(err instanceof Error ? err.message : "An error occurred during verification submission");
      setStatus("");
    } finally {
      setLoading(false);
    }
  };

  const getStatusLabel = (value: string | null | undefined) => {
    switch (value) {
      case "pending":
        return "Verification Pending";
      case "verified":
        return "Verified";
      case "rejected":
        return "Verification Rejected";
      case "resubmission_required":
        return "Resubmission Required";
      case "correction_required":
        return "Correction Required";
      case "processing":
        return "Processing";
      default:
        return "Not Submitted";
    }
  };

  const getStatusBadgeClasses = (value: string | null | undefined) => {
    switch (value) {
      case "verified":
        return "bg-green-100 text-green-800";
      case "pending":
        return "bg-yellow-100 text-yellow-800";
      case "rejected":
        return "bg-red-100 text-red-800";
      case "resubmission_required":
        return "bg-orange-100 text-orange-800";
      case "correction_required":
        return "bg-orange-100 text-orange-800";
      case "processing":
        return "bg-blue-100 text-blue-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getVerificationFeedbackReason = () => {
    return (
      currentStatus?.rejection_notes ||
      currentStatus?.admin_review_notes ||
      currentStatus?.verification_notes ||
      null
    );
  };

  const updateOcrField = <K extends keyof ExtractedNidInformation,>(
    field: K,
    value: ExtractedNidInformation[K]
  ) => {
    setOcrData((previous) => (previous ? { ...previous, [field]: value } : previous));
  };

  return (
    <div className="relative min-h-screen flex items-center justify-center bg-gray-100">
      <div className="w-full max-w-lg bg-white shadow-lg rounded-lg p-6">
        <h2 className="text-2xl font-bold text-center text-gray-800 mb-6">
          Verify Yourself
        </h2>
        <form id="nidVerificationForm" onSubmit={handleSubmit}>
          <div className="mb-4 space-y-4">
            <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_12rem] sm:items-start">
              <div>
                <label htmlFor="nidImage" className="block text-sm font-medium text-gray-700">
                  Upload an image of the front part of your NID
                </label>
                <input
                  type="file"
                  id="nidImage"
                  ref={fileInputRef}
                  accept="image/*"
                  onChange={handleFileChange}
                  disabled={isVerificationLocked}
                  className="mt-1 block w-full px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
                {file && <p className="mt-2 text-sm text-gray-600">Selected File: {file.name}</p>}
                <div className="mt-3 rounded-md border border-gray-200 bg-gray-50 p-3 text-xs text-gray-600">
                  <p className="font-medium text-gray-700">Photo tips:</p>
                  <ul className="mt-2 space-y-1">
                    <li>- Keep all four corners visible.</li>
                    <li>- Avoid glare, shadows, and blur.</li>
                    <li>- Make sure all text is readable.</li>
                  </ul>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Front Preview
                </label>
                <NIDImageDisplay
                  className="w-full h-40 object-cover border rounded-lg"
                  fallbackText="No front image yet"
                  previewImage={file}
                />
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_12rem] sm:items-start">
              <div>
                <label htmlFor="nidBackImage" className="block text-sm font-medium text-gray-700">
                  Upload an image of the back side of your NID
                </label>
                <input
                  type="file"
                  id="nidBackImage"
                  ref={backFileInputRef}
                  accept="image/*"
                  onChange={handleBackFileChange}
                  disabled={isVerificationLocked}
                  className="mt-1 block w-full px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                />
                {backFile && <p className="mt-2 text-sm text-gray-600">Selected File: {backFile.name}</p>}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Back Preview
                </label>
                <NIDImageDisplay
                  className="w-full h-40 object-cover border rounded-lg"
                  fallbackText="No back image yet"
                  previewImage={backFile}
                />
              </div>
            </div>

            <button
              type="button"
              onClick={handleExtractClick}
              disabled={isVerificationLocked || !file || !backFile || ocrStatus === "processing"}
              className="inline-flex w-full items-center justify-center rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-gray-400"
            >
              {ocrStatus === "processing" ? "Reading Your NID Information..." : "Extract NID Information"}
            </button>
          </div>

          {ocrStatus === "failed" && (
            <div className="mb-4 rounded-md bg-red-100 p-3 text-sm text-red-800">
              {ocrError || "We could not read the NID image. Please upload a clearer image and try again."}
            </div>
          )}

          {ocrStatus === "success" && ocrData && (
            <div className="mb-4 rounded-lg border border-gray-200 bg-gray-50 p-4">
              <h3 className="text-base font-semibold text-gray-800">
                Information detected from your NID:
              </h3>
              <p className="mt-1 text-sm text-gray-600">
                {isVerificationLocked
                  ? "This verification has been approved. The extracted information is now locked."
                  : "Review and edit the information extracted from your uploaded NID if needed."}
              </p>

              <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Full Name</label>
                  <input
                    type="text"
                    value={ocrData.name ?? ""}
                    onChange={(e) => updateOcrField("name", e.target.value)}
                    disabled={isVerificationLocked}
                    readOnly={isVerificationLocked}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-4 py-2 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                    placeholder="Enter full name"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Father's Name</label>
                  <input
                    type="text"
                    value={ocrData.father_name ?? ""}
                    onChange={(e) => updateOcrField("father_name", e.target.value)}
                    disabled={isVerificationLocked}
                    readOnly={isVerificationLocked}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-4 py-2 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                    placeholder="Enter father's name"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Mother's Name</label>
                  <input
                    type="text"
                    value={ocrData.mother_name ?? ""}
                    onChange={(e) => updateOcrField("mother_name", e.target.value)}
                    disabled={isVerificationLocked}
                    readOnly={isVerificationLocked}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-4 py-2 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                    placeholder="Enter mother's name"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Date of Birth</label>
                  <input
                    type="text"
                    value={ocrData.date_of_birth ?? ""}
                    onChange={(e) => updateOcrField("date_of_birth", e.target.value)}
                    disabled={isVerificationLocked}
                    readOnly={isVerificationLocked}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-4 py-2 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                    placeholder="YYYY-MM-DD"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-gray-700">NID Number</label>
                  <input
                    type="text"
                    value={ocrData.nid_number ?? ""}
                    onChange={(e) => updateOcrField("nid_number", e.target.value)}
                    disabled={isVerificationLocked}
                    readOnly={isVerificationLocked}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-4 py-2 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                    placeholder="Enter NID number"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-gray-700">Address</label>
                  <textarea
                    value={ocrData.address ?? ""}
                    onChange={(e) => updateOcrField("address", e.target.value)}
                    disabled={isVerificationLocked}
                    readOnly={isVerificationLocked}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-4 py-2 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                    placeholder="Enter address"
                    rows={3}
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-gray-700">Blood Group</label>
                  <input
                    type="text"
                    value={ocrData.blood_group ?? ""}
                    onChange={(e) => updateOcrField("blood_group", e.target.value)}
                    disabled={isVerificationLocked}
                    readOnly={isVerificationLocked}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-4 py-2 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                    placeholder="Enter blood group"
                  />
                </div>
              </div>

              {ocrData.warnings.length > 0 && (
                <div className="mt-4 rounded-md border border-yellow-200 bg-yellow-50 px-3 py-2 text-sm text-yellow-800">
                  <p className="font-medium">OCR warnings</p>
                  <ul className="mt-2 list-disc pl-5 space-y-1">
                    {ocrData.warnings.map((warning, index) => (
                      <li key={`${warning}-${index}`}>{warning}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="mt-4 space-y-3">
                <label className="flex items-start gap-2 text-sm text-gray-700">
                  <input
                    type="checkbox"
                    checked={ocrConfirmed}
                    onChange={(e) => setOcrConfirmed(e.target.checked)}
                    disabled={isVerificationLocked}
                    className="mt-1 h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
                  />
                  <span>I confirm that the information shown above belongs to me.</span>
                </label>

                <button
                  type="button"
                  onClick={handleUploadDifferentImage}
                  disabled={isVerificationLocked}
                  className="inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Upload a Different NID Image
                </button>
              </div>
            </div>
          )}

          {!canContinue && ocrStatus !== "processing" && (
            <div className="mb-4 rounded-md border border-dashed border-gray-300 bg-gray-50 px-4 py-3 text-sm text-gray-600">
              Extract and confirm the NID information to continue.
            </div>
          )}

          <div className="mb-4">
            {statusLoading ? (
              <div className="rounded-md border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-600">
                Loading verification status...
              </div>
            ) : (
              isBackendStatusVisible &&
              currentStatus && (
                <div>
                  <h3 className="text-lg font-semibold text-gray-800">Verification Status</h3>
                  <div className={`mt-2 p-3 rounded-md ${getStatusBadgeClasses(currentStatus.verification_status)}`}>
                    <p className="text-sm font-medium flex items-center">
                      {currentStatus.verification_status === "processing" && (
                        <svg className="animate-spin h-4 w-4 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                      )}
                      {getStatusLabel(currentStatus.verification_status)}
                    </p>

                    {currentStatus.verification_status === "verified" && currentStatus.verified_at && (
                      <p className="text-xs mt-2 opacity-90">
                        Verified on {new Date(currentStatus.verified_at).toLocaleString()}
                      </p>
                    )}

                    {currentStatus.verification_status === "pending" && (
                      <p className="text-xs mt-2 opacity-90">
                        Your verification request has been submitted successfully. Please wait for admin approval.
                      </p>
                    )}

                    {(currentStatus.verification_status === "rejected" || currentStatus.verification_status === "resubmission_required" || currentStatus.verification_status === "correction_required") && (
                      <p className="text-xs mt-2 opacity-90">
                        {currentStatus.verification_status === "rejected"
                          ? "Your verification was rejected. Please resubmit with corrected information."
                          : currentStatus.verification_status === "correction_required"
                            ? "Your verification requires corrections. Please review the admin feedback and update your information."
                            : "Your verification requires resubmission. Please review the admin feedback and upload a new NID image."}
                        {getVerificationFeedbackReason() && (
                          <span className="block mt-1 font-medium">
                            Reason: {getVerificationFeedbackReason()}
                          </span>
                        )}
                      </p>
                    )}

                    {currentStatus.verification_status === "processing" && (
                      <p className="text-xs mt-2 opacity-90">
                        Your verification is currently being processed.
                      </p>
                    )}

                    {(currentStatus.verification_status === "rejected" || currentStatus.verification_status === "resubmission_required" || currentStatus.verification_status === "correction_required") && (
                      <div className="mt-4 flex flex-wrap gap-3">
                        <button
                          type="button"
                          onClick={handleUploadDifferentImage}
                          className="inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
                        >
                          Upload a Different NID Image
                        </button>
                        <button
                          type="submit"
                          form="nidVerificationForm"
                          disabled={!canContinue || loading || status === "Submitting..."}
                          className="inline-flex items-center rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-gray-400"
                        >
                          Resubmit Verification
                        </button>
                      </div>
                    )}

                    {currentStatus.verification_notes && (
                      <div className="mt-3 pt-3 border-t border-opacity-20 border-gray-500">
                        <p className="text-xs opacity-75">
                          Notes: {currentStatus.verification_notes}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )
            )}
          </div>

          {canContinue && (
            <>
              <div className="mb-4">
                <label htmlFor="notes" className="block text-sm font-medium text-gray-700">
                  Additional Notes (Optional)
                </label>
                <textarea
                  id="notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="mt-1 block w-full px-4 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                  rows={3}
                  placeholder="Any additional information for the verification team..."
                />
              </div>

              {error && (
                <div className="mb-4 p-3 rounded-md bg-red-100 text-red-800">
                  <p className="text-sm font-medium">{error}</p>
                </div>
              )}

              {backendVerificationStatus !== "verified" &&
              backendVerificationStatus !== "rejected" &&
              backendVerificationStatus !== "resubmission_required" ? (
                <button
                  type="submit"
                  className={`w-full py-2 px-4 rounded-md transition ${
                    loading || status === "Submitting..." || backendVerificationStatus === "pending" || backendVerificationStatus === "verified" || backendVerificationStatus === "processing"
                      ? "bg-gray-400 cursor-not-allowed" 
                      : "bg-indigo-600 hover:bg-indigo-700"
                  } text-white`}
                  disabled={loading || status === "Submitting..." || backendVerificationStatus === "pending" || backendVerificationStatus === "verified" || backendVerificationStatus === "processing"}
                >
                  {loading || status === "Submitting..." ? (
                    <span className="flex items-center justify-center">
                      <svg className="animate-spin h-4 w-4 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Submitting...
                    </span>
                  ) : backendVerificationStatus === "pending" ? (
                    "Request Submitted - Awaiting Admin Approval"
                    ) : backendVerificationStatus === "rejected" || backendVerificationStatus === "resubmission_required" || backendVerificationStatus === "correction_required" ? (
                    "Resubmit Verification"
                  ) : (
                    "Submit Verification"
                  )}
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => navigate("/profile")}
                  className="w-full bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 transition"
                >
                  Continue to Profile
                </button>
              )}
            </>
          )}
        </form>
      </div>
    </div>
  );
};

export default NIDVerification;
