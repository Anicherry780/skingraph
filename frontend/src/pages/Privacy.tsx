import React from 'react';
import './Privacy.css';

const Privacy: React.FC = () => {
  return (
    <div className="privacy-container">
      <div className="privacy-header">
        <h1>Privacy Policy</h1>
        <p>Last updated: March 17, 2026</p>
      </div>

      <div className="privacy-content">
        <section>
          <h2>1. Information We Collect</h2>
          <p>We collect information you provide directly to us when using SkinGraph:</p>
          <ul>
            <li><strong>Account Information:</strong> If you create an account, we collect your email address or Google profile information (name, email) used for authentication.</li>
            <li><strong>Skin Profile:</strong> Information you provide about your skin type, allergies, and concerns to personalize your analysis.</li>
            <li><strong>Product Photos:</strong> Photos of product labels you upload for OCR analysis.</li>
            <li><strong>Usage Data:</strong> Products you search for, analyze, or save to your history/bookmarks.</li>
          </ul>
        </section>

        <section>
          <h2>2. How We Use Your Information</h2>
          <p>We use the collected information for the following purposes:</p>
          <ul>
            <li>To provide, maintain, and improve the SkinGraph service.</li>
            <li>To personalize your skincare analysis based on your skin profile.</li>
            <li>To allow you to track your analysis history and saved products.</li>
            <li>To process label photos using AI (Amazon Rekognition/Textract) to extract ingredients.</li>
          </ul>
        </section>

        <section>
          <h2>3. Data Storage and Security</h2>
          <p>Your data security is our priority:</p>
          <ul>
            <li><strong>Photo Uploads:</strong> Photos uploaded for label scanning are stored temporarily in Amazon S3 and are automatically deleted within 24 hours. They are not used to train AI models.</li>
            <li><strong>Account Data:</strong> Your user profile, analysis history, and saved products are stored securely using Supabase with Row Level Security (RLS), ensuring no other user can access your data.</li>
            <li><strong>Authentication:</strong> We use Supabase Auth for secure login and do not store your passwords directly (if using email/password).</li>
          </ul>
        </section>

        <section>
          <h2>4. Third-Party Services</h2>
          <p>We use third-party services to power SkinGraph:</p>
          <ul>
            <li><strong>Amazon Web Services (AWS):</strong> Used for hosting (S3) and AI analysis (Bedrock, Textract, Rekognition).</li>
            <li><strong>Supabase:</strong> Used for database and authentication.</li>
            <li><strong>Cloudflare/Render:</strong> Used for frontend and backend hosting.</li>
          </ul>
          <p>These services have their own privacy policies governing data processing.</p>
        </section>

        <section>
          <h2>5. Your Rights</h2>
          <p>You have the right to:</p>
          <ul>
            <li>Access your data through the Dashboard.</li>
            <li>Modify your skin profile and saved products.</li>
            <li>Request deletion of your account and all associated data by contacting us.</li>
          </ul>
        </section>

        <section>
          <h2>6. Contact Us</h2>
          <p>If you have any questions about this Privacy Policy, please contact us at support@skingraph.com.</p>
        </section>
      </div>
    </div>
  );
};

export default Privacy;
