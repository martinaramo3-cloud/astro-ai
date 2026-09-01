"use client";

import LegalPage from "../../components/LegalPage";

export default function PrivacyPage() {
  return (
    <LegalPage title="Privacy Policy" updated="31 August 2026">
      <p className="todo">
        Draft for legal review. Bracketed items need filling in once the company
        exists. Under GDPR this document has hard requirements &mdash; have a lawyer
        read it before launch.
      </p>

      <p>
        This explains what Zodi collects, why, and what you can do about it.{" "}
        <strong>[COMPANY NAME]</strong> is the data controller.
      </p>

      <h2>What we collect</h2>

      <h3>To make an account</h3>
      <ul>
        <li>Your name and email address</li>
        <li>Your password, stored only as a cryptographic hash &mdash; we never see it</li>
      </ul>

      <h3>To cast your chart</h3>
      <ul>
        <li>
          Your <strong>date, time, and place of birth</strong>. Zodi cannot work
          without these &mdash; they are what the whole reading is calculated from.
        </li>
      </ul>

      <div className="callout">
        <p>
          Birth details are unusually identifying. We treat them as personal data,
          we don&rsquo;t sell them, and we don&rsquo;t use them for advertising.
        </p>
      </div>

      <h3>When you use Zodi</h3>
      <ul>
        <li>The questions you ask and the answers you receive</li>
        <li>
          Birth details of anyone you choose to save as a saved person, so Zodi can
          compare charts
        </li>
        <li>How much of your plan&rsquo;s allowance you&rsquo;ve used</li>
        <li>
          <strong>Any images you attach</strong> to a question &mdash; a chart from
          another app, a screenshot of a conversation. These are stored on our
          server so the conversation still shows them when you come back, and they
          are sent to our AI providers to be read.
        </li>
      </ul>

      <div className="callout">
        <p>
          A screenshot of a conversation contains someone else&rsquo;s words, and
          they did not choose to send them to us. Please only attach what you are
          comfortable sharing. We don&rsquo;t use uploaded images to train anything,
          we don&rsquo;t show them to anyone but you, and you can delete any image
          &mdash; or all of them, by closing your account &mdash; at any time.
        </p>
      </div>

      <h3>If you subscribe</h3>
      <ul>
        <li>
          Billing is handled by our payment provider. We receive confirmation of
          payment and your plan &mdash;{" "}
          <strong>we never see or store your card details</strong>.
        </li>
      </ul>

      <h2>Why we&rsquo;re allowed to use it</h2>
      <ul>
        <li>
          <strong>To perform our contract with you</strong> &mdash; running your
          account, casting your chart, answering your questions, taking payment
        </li>
        <li>
          <strong>Our legitimate interests</strong> &mdash; keeping Zodi secure,
          preventing abuse, and fixing faults
        </li>
        <li>
          <strong>Legal obligation</strong> &mdash; keeping tax and accounting records
        </li>
      </ul>

      <h2>Who else sees your data</h2>

      <div className="callout">
        <p>
          <strong>
            Your questions and chart data are sent to AI providers so a reading can be
            written.
          </strong>{" "}
          This is the most important thing on this page. Those providers process the
          text on our behalf, under contract, and are not permitted to use it to
          train their models.
        </p>
      </div>

      <p>We use these processors:</p>
      <ul>
        <li>
          <strong>OpenAI</strong> and <strong>Anthropic</strong> &mdash; generating
          readings from your question and chart
        </li>
        <li>
          <strong>Render</strong> &mdash; hosting the application and its database
        </li>
        <li>
          <strong>Vercel</strong> &mdash; hosting the website
        </li>
        <li>
          <strong>OpenStreetMap / Nominatim</strong> &mdash; turning a birthplace into
          coordinates. Only the place name is sent, never your identity.
        </li>
        <li>
          <strong>[EMAIL PROVIDER]</strong> &mdash; sending account emails such as
          password resets
        </li>
        <li>
          <strong>[PAYMENT PROVIDER]</strong> &mdash; taking payment
        </li>
      </ul>

      <p>
        Some of these are outside the EEA. Where that&rsquo;s the case, transfers are
        covered by Standard Contractual Clauses or an equivalent safeguard.
      </p>

      <p>
        <strong>We do not sell your data</strong>, and we don&rsquo;t share it with
        advertisers.
      </p>

      <h2>How long we keep it</h2>
      <ul>
        <li>
          <strong>Your account and chart data</strong> &mdash; while your account is
          open
        </li>
        <li>
          <strong>Your conversations</strong> &mdash; until you delete them or close
          your account
        </li>
        <li>
          <strong>Images you attach</strong> &mdash; until you remove them or close
          your account, at which point the files are erased from our server, not
          just unlinked
        </li>
        <li>
          <strong>After you close your account</strong> &mdash; deleted within 30 days,
          except records we must keep for tax or legal reasons
        </li>
      </ul>

      <h2>Your rights</h2>
      <p>If you&rsquo;re in the EU or UK, you have the right to:</p>
      <ul>
        <li>See the data we hold about you</li>
        <li>Have mistakes corrected</li>
        <li>Have your data deleted</li>
        <li>Get a copy in a portable format</li>
        <li>Object to or restrict how we use it</li>
        <li>Complain to your national data protection authority</li>
      </ul>
      <p>
        To exercise any of these, email <strong>[CONTACT EMAIL]</strong>. We&rsquo;ll
        respond within one month.
      </p>
      <p className="todo">
        [Build an in-app &ldquo;download my data&rdquo; and &ldquo;delete my
        account&rdquo; before launch &mdash; these rights need a working route, not
        just an email address.]
      </p>

      <h2>Security</h2>
      <p>
        Traffic is encrypted in transit. Passwords are hashed, never stored in
        readable form. Access to the database is restricted. No system is perfectly
        secure, but if a breach ever affected your data we would tell you and the
        regulator as the law requires.
      </p>

      <h2>Cookies and similar</h2>
      <p>
        Zodi doesn&rsquo;t use advertising or tracking cookies. We store a small
        amount of information in your browser to keep you signed in and remember
        preferences such as your theme. That&rsquo;s necessary for the app to work,
        so it doesn&rsquo;t require consent.
      </p>

      <h2>Children</h2>
      <p>
        Zodi is for adults aged 18 and over. We don&rsquo;t knowingly collect data
        from children. If you believe a child has given us information, email us and
        we&rsquo;ll delete it.
      </p>

      <h2>Changes</h2>
      <p>
        If we change this policy we&rsquo;ll update the date above, and tell you by
        email if the change is significant.
      </p>

      <h2>Contact</h2>
      <p>
        <strong>[COMPANY NAME]</strong>
        <br />
        [REGISTERED ADDRESS]
        <br />
        [CONTACT EMAIL]
        <br />
        [DPO / privacy contact, if one is appointed]
      </p>
    </LegalPage>
  );
}
