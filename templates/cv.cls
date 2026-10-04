% cv.cls: one-page CV in the style of the RenderCV "classic" layout.
% All layout lives here; CV .tex files contain content only. See base/cv-technical.tex.
%
% Content commands:
%   \cvname{..} \cvlocation{..} \cvemail{..} \cvphone{display}{tel-link}
%   \cvlinkedin{url}{label}  \makecvheader
%   \section{Title}
%   \entry{Title}{Organisation}{Location}{Dates}          job / role, then a bullets env
%   \education{Institution}{Degree line}{Dates}           then optionally a bullets env
%   \educationshort{Institution}{Detail}{Dates}            one-line education entry
%   \begin{bullets} \item ... \end{bullets}                 list under an entry or a section
%   \begin{skills} \skill{Category}{items} ... \end{skills}
%   \begin{skilltable} \row{Category}{items} ... \end{skilltable}   (aligned columns)
%   \cvfooter{text}                                          footer (default: references line)
%   \href{url}{text} adds an external-link arrow; \hrefWithoutArrow{url}{text} does not.
\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{cv}[2026/10/04 CV class (RenderCV classic layout)]
\LoadClass[10pt, a4paper]{article}

% ---- Packages ------------------------------------------------------------
\RequirePackage[ignoreheadfoot, top=1.1cm, bottom=1.5cm, left=1.8cm, right=1.8cm,
                footskip=1.0cm]{geometry}
\RequirePackage{titlesec}
\RequirePackage[dvipsnames]{xcolor}
\definecolor{primaryColor}{RGB}{0, 79, 144}
\RequirePackage{enumitem}
\RequirePackage{fontawesome5}
\RequirePackage{etoolbox}
\RequirePackage[colorlinks=true, urlcolor=primaryColor]{hyperref}
\RequirePackage{calc}
\RequirePackage{bookmark}
\RequirePackage{changepage}
\RequirePackage{paracol}
\RequirePackage{ifthen}
\RequirePackage{needspace}
\RequirePackage{iftex}

% Machine-readable / ATS-parsable PDF
\ifPDFTeX
  \input{glyphtounicode}
  \pdfgentounicode=1
  \RequirePackage[T1]{fontenc}
  \RequirePackage[utf8]{inputenc}
  \RequirePackage{lmodern}
\fi

% ---- General settings ----------------------------------------------------
\AtBeginEnvironment{adjustwidth}{\partopsep0pt}
\setcounter{secnumdepth}{0}
\setlength{\parindent}{0pt}
\setlength{\topskip}{0pt}
\setlength{\columnsep}{0cm}

% Footer
\newcommand{\cv@footer}{References available upon request}
\newcommand{\cvfooter}[1]{\renewcommand{\cv@footer}{#1}}
\let\ps@customFooterStyle\ps@plain
\patchcmd{\ps@customFooterStyle}{\thepage}{\color{gray}\textit{\cv@footer}}{}{}
\pagestyle{customFooterStyle}

% ---- Sections ------------------------------------------------------------
% \ifcv@first is true right after a section title, so the first entry/list
% under a heading gets no extra gap.
\newif\ifcv@first
\newcommand{\cv@gap}{\ifcv@first\global\cv@firstfalse\else\vspace{0.10cm}\fi}
\titleformat{\section}{\needspace{4\baselineskip}\bfseries\large}{}{0pt}{}
  [\vspace{0pt}\titlerule\global\cv@firsttrue]
\titlespacing{\section}{0pt}{0.3cm}{0.2cm}

% ---- Lists and columns ---------------------------------------------------
\renewcommand\labelitemi{$\circ$}
\newenvironment{highlights}
  {\begin{itemize}[topsep=0.10cm, parsep=0.10cm, partopsep=0pt, itemsep=0pt,
                   leftmargin=0.4cm + 10pt]}
  {\end{itemize}}

\newenvironment{onecolentry}
  {\begin{adjustwidth}{0.2cm + 0.00001cm}{0.2cm + 0.00001cm}}
  {\end{adjustwidth}}

\newenvironment{twocolentry}[2][]{%
  \onecolentry
  \def\secondColumn{#2}%
  \setcolumnwidth{\fill, 5cm}%
  \begin{paracol}{2}%
}{%
  \switchcolumn \raggedleft \secondColumn
  \end{paracol}%
  \endonecolentry
}

% ---- Links ---------------------------------------------------------------
\let\hrefWithoutArrow\href
\renewcommand{\href}[2]{\hrefWithoutArrow{#1}{\ifthenelse{\equal{#2}{}}{ }{#2 }%
  \raisebox{.15ex}{\footnotesize \faExternalLink*}}}

% ---- Header --------------------------------------------------------------
\newcommand{\cv@name}{}\newcommand{\cv@location}{}\newcommand{\cv@email}{}
\newcommand{\cv@phone}{}\newcommand{\cv@phonelink}{}
\newcommand{\cv@linkedin}{}\newcommand{\cv@linkedinlabel}{}
\newcommand{\cvname}[1]{\renewcommand{\cv@name}{#1}%
  \hypersetup{pdftitle={#1's CV}, pdfauthor={#1}}}
\newcommand{\cvlocation}[1]{\renewcommand{\cv@location}{#1}}
\newcommand{\cvemail}[1]{\renewcommand{\cv@email}{#1}}
\newcommand{\cvphone}[2]{\renewcommand{\cv@phone}{#1}\renewcommand{\cv@phonelink}{#2}}
\newcommand{\cvlinkedin}[2]{\renewcommand{\cv@linkedin}{#1}\renewcommand{\cv@linkedinlabel}{#2}}

\newcommand{\cv@sep}{\kern 0.5cm}
\newcommand{\makecvheader}{%
  \begingroup
  \setlength{\topsep}{0pt}\par\kern\topsep\centering\linespread{1.5}%
  \textbf{\fontsize{18pt}{18pt}\selectfont \cv@name}\par
  \normalsize
  \mbox{{\color{black}\footnotesize\faMapMarker*}\hspace*{0.13cm}\cv@location}\cv@sep
  \mbox{\hrefWithoutArrow{mailto:\cv@email}{\color{black}{\footnotesize\faEnvelope[regular]}\hspace*{0.13cm}\cv@email}}\cv@sep
  \mbox{\hrefWithoutArrow{tel:\cv@phonelink}{\color{black}{\footnotesize\faPhone*}\hspace*{0.13cm}\cv@phone}}\cv@sep
  \mbox{\hrefWithoutArrow{\cv@linkedin}{\color{black}{\footnotesize\faLinkedinIn}\hspace*{0.13cm}\cv@linkedinlabel}}%
  \par\kern\topsep
  \endgroup}

% ---- Entries -------------------------------------------------------------
% \entry{Title}{Organisation}{Location}{Dates}
\newcommand{\entry}[4]{%
  \cv@gap
  \begin{twocolentry}{\if\relax\detokenize{#3}\relax\else\textit{#3}\par\fi\textit{#4}}
    \textbf{#1}\par
    \textit{#2}
  \end{twocolentry}}

% \education{Institution}{Degree line}{Dates}
\newcommand{\education}[3]{%
  \cv@gap
  \begin{twocolentry}{\textit{#3}}
    \textbf{#1}\newline
    \textit{#2}
  \end{twocolentry}}

% \educationshort{Institution}{Detail}{Dates}
\newcommand{\educationshort}[3]{%
  \cv@gap
  \begin{twocolentry}{\textit{#3}}
    \textbf{#1} -- \textit{#2}
  \end{twocolentry}}

% Bullet list: under an entry, or directly under a section
\newenvironment{bullets}
  {\cv@gap\begin{onecolentry}\begin{highlights}}
  {\end{highlights}\end{onecolentry}}

% Skills block: one \skill per line
\newenvironment{skills}{\cv@gap\begin{onecolentry}}{\end{onecolentry}}
\newcommand{\skill}[2]{\textbf{#1:} #2\par}

% Aligned skills table: \row{Category}{items} per line.
% Label column width: \setlength{\skilllabelwidth}{3.4cm} in the .tex if needed.
\newlength{\skilllabelwidth}
\setlength{\skilllabelwidth}{3.3cm}
\newenvironment{skilltable}{\cv@gap\begin{onecolentry}}{\end{onecolentry}}
\newcommand{\row}[2]{%
  \noindent\makebox[\skilllabelwidth][l]{\textbf{#1}}%
  \parbox[t]{\linewidth-\skilllabelwidth}{#2}\par}
