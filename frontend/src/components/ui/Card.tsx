import type { HTMLAttributes, ReactNode } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  /** Adds default padding to the card body */
  padded?: boolean;
}

interface CardHeaderProps extends HTMLAttributes<HTMLDivElement> {
  title: string;
  actions?: ReactNode;
}

function CardHeader({ title, actions, className = "", ...props }: CardHeaderProps) {
  return (
    <div className={`card-header ${className}`} {...props}>
      <span className="card-title">{title}</span>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

function CardBody({ children, className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`card-body ${className}`} {...props}>
      {children}
    </div>
  );
}

export function Card({ children, padded = false, className = "", ...props }: CardProps) {
  return (
    <div className={`card ${padded ? "card-padded" : ""} ${className}`} {...props}>
      {children}
    </div>
  );
}

Card.Header = CardHeader;
Card.Body = CardBody;
