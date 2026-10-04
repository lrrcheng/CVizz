% coverletter.cls: one-page cover letter with a plain sender block.
% All layout lives here; application .tex files contain content only.
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{coverletter}[2026/10/04 Cover letter class]
\LoadClass[11pt]{article}

\RequirePackage[T1]{fontenc}
\RequirePackage[utf8]{inputenc}
\RequirePackage{lmodern}
\RequirePackage[a4paper, top=2.2cm, bottom=2.2cm, left=2.5cm, right=2.5cm]{geometry}
\RequirePackage[hidelinks]{hyperref}
\RequirePackage{microtype}

\pagestyle{empty}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0.8em}

% \sender{Name}{Location}{Email}{Phone}
\newcommand{\sender}[4]{%
  {\setlength{\parskip}{0pt}
  \textbf{#1}\\ #2\\ \href{mailto:#3}{#3}\\ #4\par}\vspace{0.6em}}

% \recipient{Date}{Company}{Optional second line, e.g. city}
\newcommand{\recipient}[3]{%
  {\setlength{\parskip}{0pt}
  #1\par\vspace{0.8em}
  #2\if\relax\detokenize{#3}\relax\else\\ #3\fi\par}\vspace{0.4em}}

% \subject{Application for ...}
\newcommand{\subject}[1]{\textbf{#1}\par}

% \closing{Kind regards,}{Name}
\newcommand{\closing}[2]{\vspace{0.2em}#1\\[0.2em]#2}
