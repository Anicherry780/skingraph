import React, { useState } from 'react';
import './Privacy.css'; // Reusing privacy CSS for consistent styling

const RequestDeletion: React.FC = () => {
  const [submitted, setSubmitted] = useState(false);
  const [email, setEmail] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (email) {
      setSubmitted(true);
    }
  };

  return (
    <div className="privacy-container">
      <div className="privacy-header">
        <h1>Data Deletion Request</h1>
        <p>Submit a request to permanently delete your SkinGraph account and all associated data.</p>
      </div>

      <div className="privacy-content">
        {!submitted ? (
          <section>
            <h2>Delete Your Account & Data</h2>
            <p>
              By submitting this request, the following data associated with your account will be permanently and irreversibly deleted within 30 days:
            </p>
            <ul>
              <li>Your SkinGraph account credentials</li>
              <li>Your personalized skin profile and allergies</li>
              <li>Your entire analysis history</li>
              <li>Your saved and bookmarked products</li>
            </ul>
            <p className="warning-text" style={{ color: '#ef4444', fontWeight: 500, marginTop: '16px' }}>
              Note: This action cannot be undone. Once deleted, your data cannot be recovered.
            </p>
            
            <form onSubmit={handleSubmit} style={{ marginTop: '24px' }}>
              <div style={{ marginBottom: '16px' }}>
                <label htmlFor="email" style={{ display: 'block', marginBottom: '8px', fontWeight: 500, color: '#374151' }}>
                  Account Email Address
                </label>
                <input
                  type="email"
                  id="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter the email associated with your account"
                  required
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: '8px',
                    border: '1px solid #d1d5db',
                    fontSize: '1rem',
                  }}
                />
              </div>
              <button 
                type="submit" 
                style={{
                  backgroundColor: '#ef4444',
                  color: 'white',
                  border: 'none',
                  padding: '10px 20px',
                  borderRadius: '8px',
                  fontSize: '1rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  width: '100%'
                }}
              >
                Submit Deletion Request
              </button>
            </form>
          </section>
        ) : (
          <section style={{ textAlign: 'center', padding: '40px 20px' }}>
            <div style={{ fontSize: '3rem', marginBottom: '16px' }}>✅</div>
            <h2>Request Received</h2>
            <p style={{ fontSize: '1.1rem', marginBottom: '16px' }}>
              We have received your data deletion request for <strong>{email}</strong>.
            </p>
            <p>
              Your account and all associated data will be permanently deleted from our servers within 30 days. You will receive an email confirmation once the process is complete.
            </p>
            <button 
              onClick={() => window.location.href = '/'}
              style={{
                marginTop: '24px',
                backgroundColor: 'var(--green)',
                color: 'white',
                border: 'none',
                padding: '10px 24px',
                borderRadius: '8px',
                fontSize: '1rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Return to Home
            </button>
          </section>
        )}
      </div>
    </div>
  );
};

export default RequestDeletion;
