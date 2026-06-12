import React, { useState, useEffect } from 'react';
import { getAccessToken, API_BASE_URL } from '../services/api';

interface NIDImageDisplayProps {
  userId?: string; // If provided, shows image for specific user (admin view)
  className?: string;
  fallbackText?: string;
  previewImage?: File | null; // For showing preview of newly selected image
}

const NIDImageDisplay: React.FC<NIDImageDisplayProps> = ({
  userId,
  className = "w-full h-48 object-cover border rounded-lg",
  fallbackText = "No NID image uploaded",
  previewImage = null
}) => {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (previewImage) {
      const url = URL.createObjectURL(previewImage);
      setImageUrl(url);
      setLoading(false);
      setError(null);
      return () => {
        URL.revokeObjectURL(url);
      };
    }

    const fetchImage = async () => {
      try {
        setLoading(true);
        setError(null);

        // Get auth token
        const token = getAccessToken();
        if (!token) {
          throw new Error('Authentication required');
        }

        // Determine endpoint based on whether userId is provided
        const endpoint = userId 
          ? `${API_BASE_URL}/verification/image/${userId}`
          : `${API_BASE_URL}/verification/image`;

        const response = await fetch(endpoint, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (response.status === 404) {
          setError(fallbackText);
          return;
        }

        if (!response.ok) {
          throw new Error(`Failed to load image: ${response.status}`);
        }

        // Convert response to blob and create object URL
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        setImageUrl(url);

      } catch (err) {
        console.error('Error loading NID image:', err);
        setError(err instanceof Error ? err.message : 'Failed to load image');
      } finally {
        setLoading(false);
      }
    };

    fetchImage();

    // Cleanup function to revoke object URL
    return () => {
      if (imageUrl) {
        URL.revokeObjectURL(imageUrl);
      }
    };
  }, [userId, fallbackText, previewImage]);

  // Cleanup object URL when component unmounts
  useEffect(() => {
    return () => {
      if (imageUrl) {
        URL.revokeObjectURL(imageUrl);
      }
    };
  }, [imageUrl]);

  if (loading) {
    return (
      <div className={`${className} flex items-center justify-center bg-gray-100`}>
        <div className="flex flex-col items-center">
          <svg className="animate-spin h-8 w-8 text-gray-400 mb-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span className="text-sm text-gray-500">Loading image...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`${className} flex items-center justify-center bg-gray-100 text-gray-500`}>
        <div className="flex flex-col items-center">
          <svg className="h-8 w-8 text-gray-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <span className="text-sm text-center">{error}</span>
        </div>
      </div>
    );
  }

  return imageUrl ? (
    <img
      src={imageUrl}
      alt="NID Document"
      className={className}
      onError={() => setError('Failed to display image')}
    />
  ) : null;
};

export default NIDImageDisplay;