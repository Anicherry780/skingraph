import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import './Privacy.css';

const RequestDeletion: React.FC = () => {
  const { user, deleteAccount } = useAuth();
  const [submitted, setSubmitted] = useState(false);
  const [email, setEmail] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleManualRequest = (e: React.FormEvent) => {
    e.preventDefault();
    if (email) {
      setSubmitted(true);
    }
  };

  const handleAuthenticatedDelete = async () => {
    if (!window.confirm("Are you absolutely sure? This will instantly and permanently delete your account, history, and saved products. This CANNOT be undone.")) {
      return;
    }
    
    setIsDeleting(true);
    setError(null);
    
    const { error: deleteError } = await deleteAccount();
    
    if (deleteError) {
      setError(deleteError);
      setIsDeleting(false);
    } else {
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
            
            {error && (
              <div style={{ padding: '12px', backgroundColor: '#fef2f2', color: '#991b1b', borderRadius: '8px', marginTop: '16px', border: '1px solid #f87171' }}>
                {error}
              </div>
            )}
            
            {user ? (
              <div style={{ marginTop: '24px', padding: '20px', backgroundColor: '#fff5f5', borderRadius: '8px', border: '1px solid #fecaca' }}>
                <h3 style={{ marginTop: 0, color: '#991b1b' }}>You are logged in as {user.email}</h3>
                <p style={{ marginBottom: '16px', color: '#7f1d1d' }}>You can instantly and permanently delete your account right now.</p>
                <button 
                  onClick={handleAuthenticatedDelete}
                  disabled={isDeleting}
                  style={{
                    backgroundColor: '#ef4444',
                    color: 'white',
                    border: 'none',
                    padding: '12px 24px',
                    borderRadius: '8px',
                    fontSize: '1rem',
                    fontWeight: 600,
                    cursor: isDeleting ? 'not-allowed' : 'pointer',
                    width: '100%',
                    opacity: isDeleting ? 0.7 : 1
                  }}
                >
                  {isDeleting ? 'Deleting your data...' : 'Permanently Delete My Account'}
                </button>
              </div>
            ) : (
              <div style={{ marginTop: '24px' }}>
                <div style={{ padding: '16px', backgroundColor: '#f3f4f6', borderRadius: '8px', marginBottom: '24px' }}>
                  <strong>Want instant deletion?</strong> <a href="/auth" style={{ color: 'var(--green)', textDecoration: 'underline' }}>Log in to your account</a> to delete it instantly without waiting for manual processing.
                </div>
                
                <h3 style={{ marginTop: 0 }}>Or submit a manual request:</h3>
                <form onSubmit={handleManualRequest} style={{ marginTop: '16px' }}>
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
                      backgroundColor: '#4b5563',
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
                    Submit Manual Deletion Request
                  </button>
                </form>
              </div>
            )}
          </section>
        ) : (
          <section style={{ textAlign: 'center', padding: '40px 20px' }}>
            <div style={{ fontSize: '3rem', marginBottom: '16px' }}>✅</div>
            <h2>{user ? 'Account Deleted' : 'Request Received'}</h2>
            <p style={{ fontSize: '1.1rem', marginBottom: '16px' }}>
              {user ? (
                'Your account and all associated data have been permanently deleted.'
              ) : (
                <>We have received your manual data deletion request for <strong>{email}</strong>.</>
              )}
            </p>
            {!user && (
              <p>
                Your account and all associated data will be permanently deleted from our servers within 30 days. You will receive an email confirmation once the process is complete.
              </p>
            )}
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
