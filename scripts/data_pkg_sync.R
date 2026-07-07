#!/usr/bin/env Rscript
# data_pkg_sync.R - sync registered R data packages into the vault
# (data-package seam, specs/ingest.md REQ-100..106, issues #92/#93).
#
# An R data package is a versioned dataset bundle: DESCRIPTION (version,
# license, URL), data/*.rda (canonical objects), inst/extdata/*.csv
# (portable copies), man/*.Rd (description + per-variable dictionary).
# Each sync writes ONE versioned snapshot ingested/data/<pkg>-<version>/
# and creates/refreshes one wiki/data/<pkg>/<dataset> page per dataset.
#
# The lit_sync.py contract applies:
#   - managed properties and the machine-managed sections
#     ("## description", "## data dictionary") are regenerated each sync
#     (ingest REQ-102); everything else on the page is never touched
#   - old snapshots stay put: cite::/source-file:: refs to them remain
#     valid after a version bump (REQ-103)
#   - retention keeps the last N snapshots (data_snapshots_keep, default
#     3) and NEVER deletes a snapshot referenced by any page (REQ-105)
#
# Base R + tools only; no package dependencies.
#
# Usage:
#   Rscript scripts/data_pkg_sync.R --check  [--config <llm-wiki.yml>]
#   Rscript scripts/data_pkg_sync.R [--dry-run] [--pkg <owner/repo>]
#                                   [--local <package-dir>]
#                                   [--config <llm-wiki.yml>]
#
# --check compares each registered package's GitHub DESCRIPTION Version
# against the newest local snapshot; exit 1 when anything is stale;
# never writes (REQ-106). Without --check the script syncs (all
# registered packages, or one via --pkg, or a local checkout via
# --local). --dry-run prints the plan and writes nothing (the /data-sync
# checkpoint runs on it, REQ-104).
#
# Exit codes: 0 ok / nothing stale, 1 stale (--check) or bad arguments,
# 2 download/parse failure.

suppressWarnings(suppressMessages(library(tools)))

# --- minimal flat-YAML config (mirrors wikilib.parse_config_text) ---------

parse_config <- function(path) {
  lines <- readLines(path, warn = FALSE)
  config <- list()
  open_key <- NULL
  for (line in lines) {
    stripped <- trimws(line)
    if (stripped == "" || startsWith(stripped, "#")) next
    if (grepl("^\\s*-\\s+", line) && !is.null(open_key)) {
      item <- trimws(sub("^\\s*-\\s+", "", line))
      config[[open_key]] <- c(config[[open_key]], item)
      next
    }
    key_match <- regmatches(line, regexec("^([A-Za-z0-9_]+):\\s*(.*)$", line))[[1]]
    if (length(key_match) == 3) {
      key <- key_match[2]
      value <- trimws(key_match[3])
      config[[key]] <- value
      open_key <- if (value == "") key else NULL
    } else {
      open_key <- NULL
    }
  }
  config
}

discover_config <- function(explicit) {
  if (!is.null(explicit)) {
    if (!file.exists(explicit)) stop("config not found: ", explicit)
    return(normalizePath(explicit))
  }
  env <- Sys.getenv("LLM_WIKI_CONFIG", "")
  if (nzchar(env) && file.exists(env)) return(normalizePath(env))
  dir <- normalizePath(getwd())
  home <- normalizePath(path.expand("~"))
  repeat {
    candidate <- file.path(dir, "llm-wiki.yml")
    if (file.exists(candidate)) return(candidate)
    if (dir == home || dirname(dir) == dir) break
    dir <- dirname(dir)
  }
  pointer <- path.expand("~/.config/llm-wiki/config.yml")
  if (file.exists(pointer)) {
    wiki_path <- path.expand(parse_config(pointer)[["wiki_path"]] %||% "")
    candidate <- file.path(wiki_path, "llm-wiki.yml")
    if (nzchar(wiki_path) && file.exists(candidate)) return(candidate)
  }
  stop("llm-wiki.yml not found. Run /wiki-setup to create one.")
}

`%||%` <- function(a, b) if (is.null(a)) b else a

# --- Rd extraction ---------------------------------------------------------

rd_text <- function(node) {
  if (is.character(node)) return(paste(node, collapse = ""))
  if (is.list(node)) return(paste(vapply(node, rd_text, ""), collapse = ""))
  ""
}

rd_find <- function(rd, tag) {
  hits <- list()
  for (node in rd) {
    node_tag <- attr(node, "Rd_tag")
    if (identical(node_tag, tag)) hits[[length(hits) + 1]] <- node
    if (is.list(node)) hits <- c(hits, rd_find(node, tag))
  }
  hits
}

rd_first <- function(rd, tag) {
  hits <- rd_find(rd, tag)
  if (length(hits)) hits[[1]] else NULL
}

clean_ws <- function(text) trimws(gsub("\\s+", " ", text))

# Returns list(name=, title=, description=, source=, vars=data.frame)
parse_dataset_rd <- function(path) {
  rd <- tryCatch(tools::parse_Rd(path), error = function(e) NULL)
  if (is.null(rd)) return(NULL)
  doc_types <- vapply(rd_find(rd, "\\docType"), rd_text, "")
  if (!any(trimws(doc_types) == "data")) return(NULL)
  name <- clean_ws(rd_text(rd_first(rd, "\\name")))
  title <- clean_ws(rd_text(rd_first(rd, "\\title")))
  description <- clean_ws(rd_text(rd_first(rd, "\\description")))
  source_text <- clean_ws(rd_text(rd_first(rd, "\\source")))
  vars <- data.frame(name = character(), description = character(),
                     stringsAsFactors = FALSE)
  for (item in rd_find(rd, "\\item")) {
    # \describe items have exactly two argument blocks: name, description
    if (is.list(item) && length(item) == 2) {
      vars <- rbind(vars, data.frame(
        name = clean_ws(rd_text(item[[1]])),
        description = clean_ws(rd_text(item[[2]])),
        stringsAsFactors = FALSE))
    }
  }
  list(name = name, title = title, description = description,
       source = source_text, vars = vars)
}

# --- package acquisition ---------------------------------------------------

fetch_description_version <- function(slug) {
  url <- sprintf("https://raw.githubusercontent.com/%s/HEAD/DESCRIPTION", slug)
  lines <- tryCatch(readLines(url, warn = FALSE), error = function(e) NULL)
  if (is.null(lines)) return(NULL)
  version_line <- grep("^Version:", lines, value = TRUE)
  if (!length(version_line)) return(NULL)
  trimws(sub("^Version:", "", version_line[1]))
}

download_package <- function(slug) {
  url <- sprintf("https://codeload.github.com/%s/tar.gz/HEAD", slug)
  tarball <- tempfile(fileext = ".tar.gz")
  ok <- tryCatch({
    utils::download.file(url, tarball, quiet = TRUE, mode = "wb")
    TRUE
  }, error = function(e) FALSE, warning = function(w) FALSE)
  if (!ok) {
    message("data_pkg_sync: cannot download ", slug, " from GitHub. ",
            "Check the slug and your network; STOP here.")
    quit(status = 2)
  }
  exdir <- tempfile("pkg")
  utils::untar(tarball, exdir = exdir)
  roots <- list.dirs(exdir, recursive = FALSE)
  if (length(roots) != 1) {
    message("data_pkg_sync: unexpected tarball layout for ", slug)
    quit(status = 2)
  }
  roots[1]
}

local_snapshot_versions <- function(ingested_data, pkg) {
  dirs <- list.dirs(ingested_data, recursive = FALSE, full.names = FALSE)
  pattern <- paste0("^", pkg, "-")
  versions <- sub(pattern, "", dirs[grepl(pattern, dirs)])
  versions[order(numeric_version(versions, strict = FALSE))]
}

# --- vault page writing ----------------------------------------------------

MANAGED_PROPS <- c("package", "version", "license", "url",
                   "source-file", "data-last-sync", "updated")

page_separator <- function(pages_dir) {
  if (any(grepl("%2F", list.files(pages_dir)))) "%2F" else "___"
}

page_file <- function(pages_dir, parts, separator) {
  file.path(pages_dir, paste0(paste(parts, collapse = separator), ".md"))
}

prop_line <- function(key, value) sprintf("%s:: %s", key, value)

# Replace the content of a machine-managed top-level block
# ("- ## description", "- ## data dictionary"), REQ-102: single-indent
# children are machine rows and are regenerated; DEEPER-indented lines
# (the user's annotations under a row) are preserved, appended after the
# fresh rows. Free-standing notes belong under "## fleeting" (issue
# #100; "## my notes" on pages created before the rename), which is
# never touched. Appends the block at EOF when absent.
replace_managed_block <- function(lines, heading, children) {
  idx <- which(trimws(lines) == paste0("- ", heading))
  if (!length(idx)) {
    if (length(lines) && nzchar(trimws(lines[length(lines)])))
      lines <- c(lines, "")
    return(c(lines, paste0("- ", heading), children))
  }
  start <- idx[1]
  end <- start + 1
  preserved <- character()
  while (end <= length(lines) &&
         (grepl("^[\t ]", lines[end]) || !nzchar(trimws(lines[end])))) {
    if (grepl("^(\t{2,}|[ ]{4,})", lines[end]))
      preserved <- c(preserved, lines[end])
    end <- end + 1
  }
  c(lines[seq_len(start - 1)], paste0("- ", heading), children, preserved,
    if (end <= length(lines)) lines[end:length(lines)] else character())
}

update_properties <- function(lines, values) {
  prop_re <- "^([A-Za-z0-9][A-Za-z0-9-]*)::\\s*(.*)$"
  end <- 0
  for (line in lines) {
    if (grepl(prop_re, line)) end <- end + 1 else break
  }
  block <- if (end) lines[seq_len(end)] else character()
  rest <- if (end < length(lines)) lines[(end + 1):length(lines)] else character()
  seen <- character()
  for (i in seq_along(block)) {
    key <- sub(prop_re, "\\1", block[i])
    if (key %in% names(values)) {
      block[i] <- prop_line(key, values[[key]])
      seen <- c(seen, key)
    }
  }
  for (key in setdiff(names(values), seen))
    block <- c(block, prop_line(key, values[[key]]))
  c(block, rest)
}

# Each dictionary row is a claim; cite:: rides it as a block property
# (the indented continuation line, citations REQ-900 shape).
dictionary_children <- function(info, doc_ref) {
  if (!nrow(info$vars))
    return("\t- (no variable dictionary in the package docs)")
  rows <- sprintf("\t- %s - %s", info$vars$name, info$vars$description)
  cites <- rep(sprintf("\t  cite:: %s", doc_ref), length(rows))
  as.vector(rbind(rows, cites))
}

write_dataset_page <- function(path, pkg, slug, version, license, url_field,
                               info, snapshot_rel, dims, dry_run) {
  today <- format(Sys.Date())
  csv_ref <- sprintf("%s/%s.csv", snapshot_rel, info$name)
  doc_ref <- sprintf("%s/%s.md", snapshot_rel, info$name)
  values <- list(
    "package" = pkg, "version" = version, "license" = license,
    "url" = url_field,
    "source-file" = paste(csv_ref, doc_ref, sep = ", "),
    "data-last-sync" = version, "updated" = today)
  description_children <- c(
    sprintf("\t- %s", if (nzchar(info$description)) info$description else info$title),
    sprintf("\t  cite:: %s", doc_ref),
    sprintf("\t- %d rows, %d variables (data: %s)", dims[1], dims[2], csv_ref),
    sprintf("\t  cite:: %s", csv_ref))

  if (file.exists(path)) {
    lines <- readLines(path, warn = FALSE)
    lines <- update_properties(lines, values)
    action <- "update"
  } else {
    lines <- c(
      prop_line("type", "entity"),
      prop_line("entity-type", "dataset"),
      prop_line("created", today),
      prop_line("status", "active"),
      prop_line("source", "ingest"),
      prop_line("reliability", "high"),
      prop_line("schema-spec-version", "2.0.0"),
      vapply(names(values), function(k) prop_line(k, values[[k]]), ""),
      "",
      sprintf("- %s", info$title),
      sprintf("  cite:: %s", doc_ref),
      "- ## fleeting",
      "\t- ",
      "- ## Cross-References",
      sprintf("\t- [[wiki/data/%s]]", pkg))
    action <- "create"
  }
  lines <- replace_managed_block(lines, "## description", description_children)
  lines <- replace_managed_block(lines, "## data dictionary",
                                 dictionary_children(info, doc_ref))
  if (!dry_run) writeLines(lines, path)
  action
}

upsert_routing_line <- function(hub_path, link, description, dry_run) {
  line <- sprintf("\t- [[%s]] -- %s", link, description)
  if (!file.exists(hub_path)) return(sprintf("MISSING hub %s (add: %s)",
                                             basename(hub_path), line))
  lines <- readLines(hub_path, warn = FALSE)
  hit <- grep(sprintf("[[%s]]", link), lines, fixed = TRUE)
  if (length(hit)) {
    lines[hit[1]] <- line
  } else {
    index_at <- grep("^\\s*-?\\s*### Index", lines)
    if (!length(index_at)) return(sprintf("hub %s has no ### Index",
                                          basename(hub_path)))
    lines <- append(lines, line, after = index_at[1])
  }
  if (!dry_run) writeLines(lines, hub_path)
  NULL
}

ensure_hub <- function(pages_dir, separator, parts, title, dry_run) {
  path <- page_file(pages_dir, parts, separator)
  if (file.exists(path)) return(path)
  today <- format(Sys.Date())
  lines <- c(prop_line("type", "hub"),
             prop_line("namespace", paste(parts, collapse = "/")),
             prop_line("created", today),
             prop_line("updated", today), prop_line("status", "active"),
             prop_line("source", "manual"),
             prop_line("schema-spec-version", "2.0.0"), "",
             sprintf("- %s", title), "- ### Index")
  if (!dry_run) writeLines(lines, path)
  path
}

# --- retention (REQ-105) ---------------------------------------------------

prune_snapshots <- function(ingested_data, pkg, keep, pages_dir, dry_run) {
  versions <- local_snapshot_versions(ingested_data, pkg)
  if (length(versions) <= keep) return(invisible())
  drop <- head(versions, length(versions) - keep)
  page_text <- paste(unlist(lapply(
    list.files(pages_dir, pattern = "\\.md$", full.names = TRUE),
    readLines, warn = FALSE)), collapse = "\n")
  for (version in drop) {
    rel <- sprintf("ingested/data/%s-%s/", pkg, version)
    if (grepl(rel, page_text, fixed = TRUE)) {
      cat(sprintf("retain  %s (referenced by a page, REQ-105)\n", rel))
      next
    }
    cat(sprintf("prune   %s\n", rel))
    if (!dry_run) unlink(file.path(ingested_data,
                                   sprintf("%s-%s", pkg, version)),
                         recursive = TRUE)
  }
}

# --- sync one package ------------------------------------------------------

sync_package <- function(slug, local_dir, config, wiki_path, pages_dir,
                         dry_run) {
  pkg_dir <- if (!is.null(local_dir)) local_dir else download_package(slug)
  desc_path <- file.path(pkg_dir, "DESCRIPTION")
  if (!file.exists(desc_path)) {
    message("data_pkg_sync: no DESCRIPTION in ", pkg_dir); quit(status = 2)
  }
  desc <- read.dcf(desc_path)
  pkg <- desc[1, "Package"]
  version <- desc[1, "Version"]
  license <- if ("License" %in% colnames(desc)) desc[1, "License"] else ""
  url_field <- if (!is.null(slug)) sprintf("https://github.com/%s", slug)
               else if ("URL" %in% colnames(desc)) trimws(strsplit(
                 desc[1, "URL"], ",")[[1]][1]) else ""

  ingested_data <- file.path(wiki_path,
                             config[["ingested_dir"]] %||% "ingested", "data")
  snapshot_rel <- sprintf("ingested/data/%s-%s", pkg, version)
  snapshot_dir <- file.path(ingested_data, sprintf("%s-%s", pkg, version))
  if (dir.exists(snapshot_dir)) {
    cat(sprintf("skip    %s (snapshot %s already exists)\n", pkg, version))
    return(invisible())
  }
  if (!dry_run) dir.create(snapshot_dir, recursive = TRUE)

  # 1. materialize data/*.rda data frames to CSV
  datasets <- character()
  dims_by_dataset <- list()
  for (rda in list.files(file.path(pkg_dir, "data"),
                         pattern = "\\.(rda|RData)$", full.names = TRUE)) {
    env <- new.env()
    load(rda, envir = env)
    for (obj_name in ls(env)) {
      obj <- get(obj_name, envir = env)
      if (is.data.frame(obj)) {
        datasets <- c(datasets, obj_name)
        dims_by_dataset[[obj_name]] <- dim(obj)
        if (!dry_run)
          utils::write.csv(obj, file.path(snapshot_dir,
                                          paste0(obj_name, ".csv")),
                           row.names = FALSE)
      }
    }
  }
  # 2. copy inst/extdata CSVs
  for (csv in list.files(file.path(pkg_dir, "inst", "extdata"),
                         pattern = "\\.csv$", full.names = TRUE)) {
    dataset <- tools::file_path_sans_ext(basename(csv))
    datasets <- c(datasets, dataset)
    if (is.null(dims_by_dataset[[dataset]])) {
      header <- utils::read.csv(csv, nrows = 1)
      dims_by_dataset[[dataset]] <- c(length(readLines(csv, warn = FALSE)) - 1L,
                                      ncol(header))
    }
    if (!dry_run) file.copy(csv, snapshot_dir)
  }
  datasets <- unique(datasets)

  # 3. extract Rd docs
  infos <- list()
  for (rd_path in list.files(file.path(pkg_dir, "man"), pattern = "\\.Rd$",
                             full.names = TRUE)) {
    info <- parse_dataset_rd(rd_path)
    if (!is.null(info)) infos[[info$name]] <- info
  }
  for (dataset in datasets) {
    info <- infos[[dataset]] %||% list(
      name = dataset, title = dataset, description = "",
      source = "", vars = data.frame(name = character(),
                                     description = character()))
    doc <- c(sprintf("# %s", info$name), "",
             info$title, "",
             info$description, "",
             "## variables", "",
             if (nrow(info$vars))
               sprintf("- %s: %s", info$vars$name, info$vars$description)
             else "- (no variable dictionary in the package docs)",
             "",
             if (nzchar(info$source)) c("## source", "", info$source)
             else character(),
             "",
             sprintf("provenance: %s %s | %s | synced %s", pkg, version,
                     url_field, format(Sys.Date())))
    if (!dry_run) writeLines(doc, file.path(snapshot_dir,
                                            paste0(dataset, ".md")))
  }

  # 4. dataset pages + routing
  separator <- page_separator(pages_dir)
  ensure_hub(pages_dir, separator, c("wiki", "data"), "Data hub", dry_run)
  pkg_hub <- ensure_hub(pages_dir, separator, c("wiki", "data", pkg),
                        sprintf("Datasets of the %s package", pkg), dry_run)
  upsert_routing_line(
    page_file(pages_dir, c("wiki", "data"), separator),
    sprintf("wiki/data/%s", pkg),
    sprintf("R data package %s %s #data", pkg, version), dry_run)
  for (dataset in datasets) {
    info <- infos[[dataset]] %||% list(name = dataset, title = dataset,
                                       description = "", source = "",
                                       vars = data.frame(
                                         name = character(),
                                         description = character()))
    path <- page_file(pages_dir, c("wiki", "data", pkg, dataset), separator)
    action <- write_dataset_page(path, pkg, slug, version, license,
                                 url_field, info, snapshot_rel,
                                 dims_by_dataset[[dataset]] %||% c(0L, 0L),
                                 dry_run)
    cat(sprintf("%-7s %s\n", action, basename(path)))
    upsert_routing_line(
      pkg_hub, sprintf("wiki/data/%s/%s", pkg, dataset),
      sprintf("%s #data", substr(info$title, 1, 100)), dry_run)
  }

  cat(sprintf("snapshot %s (%d datasets)%s\n", snapshot_rel,
              length(datasets),
              if (dry_run) " [dry-run, nothing written]" else ""))

  # 5. retention
  keep <- suppressWarnings(as.integer(config[["data_snapshots_keep"]] %||% "3"))
  if (is.na(keep) || keep < 1) keep <- 3
  prune_snapshots(ingested_data, pkg, keep, pages_dir, dry_run)
}

# --- modes -----------------------------------------------------------------

run_check <- function(slugs, wiki_path, config) {
  ingested_data <- file.path(wiki_path,
                             config[["ingested_dir"]] %||% "ingested", "data")
  stale <- 0
  for (slug in slugs) {
    remote <- fetch_description_version(slug)
    pkg <- basename(slug)
    versions <- local_snapshot_versions(ingested_data, pkg)
    local <- if (length(versions)) tail(versions, 1) else "(none)"
    if (is.null(remote)) {
      cat(sprintf("?       %-30s local %s, remote unreachable\n", slug, local))
    } else if (identical(remote, local)) {
      cat(sprintf("current %-30s %s\n", slug, local))
    } else {
      cat(sprintf("STALE   %-30s local %s, GitHub %s -> run /data-sync\n",
                  slug, local, remote))
      stale <- stale + 1
    }
  }
  quit(status = if (stale) 1 else 0)
}

main <- function() {
  args <- commandArgs(trailingOnly = TRUE)
  get_opt <- function(flag) {
    hit <- which(args == flag)
    if (length(hit) && hit[1] < length(args)) args[hit[1] + 1] else NULL
  }
  config_path <- discover_config(get_opt("--config"))
  config <- parse_config(config_path)
  wiki_path <- path.expand(config[["wiki_path"]] %||% "")
  pages_dir <- file.path(wiki_path, config[["pages_dir"]] %||% "pages")
  if (!dir.exists(pages_dir)) stop("pages dir not found: ", pages_dir)

  slugs <- config[["data_packages"]]
  dry_run <- "--dry-run" %in% args
  local_dir <- get_opt("--local")
  one_pkg <- get_opt("--pkg")

  if ("--check" %in% args) {
    if (is.null(slugs)) stop("no data_packages configured (config REQ-660)")
    run_check(slugs, wiki_path, config)
  }
  if (!is.null(local_dir)) {
    sync_package(NULL, normalizePath(local_dir), config, wiki_path,
                 pages_dir, dry_run)
  } else {
    if (is.null(slugs)) stop("no data_packages configured (config REQ-660)")
    if (!is.null(one_pkg)) slugs <- one_pkg
    for (slug in slugs)
      sync_package(slug, NULL, config, wiki_path, pages_dir, dry_run)
  }
}

main()
