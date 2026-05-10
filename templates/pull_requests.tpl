% rebase("base.tpl", title=repo["owner_username"] + "/" + repo["name"] + " pull requests", user=user, error=error, notice=notice)
% q = get("q", "")
% pull_request_scope = "pull requests" if status == "all" else status + " pull requests"

<section class="repo-header slim">
  <div>
    % include("repo_fork_eyebrow.tpl")
    % include("repo_title.tpl", repo=repo)
    
    % include("repo_nav.tpl", repo=repo, commit_count=commit_count, issue_counts=issue_counts, pr_counts=pr_counts, star_count=star_count, is_starred=is_starred, is_owner=is_owner, can_maintain=can_maintain)
    
  </div>
</section>

<section class="panel">
  <div class="panel-heading">
      <form class="repo-search-form" action="/{{repo['owner_username']}}/{{repo['name']}}/pulls" method="get" role="search" data-live-search-form data-live-search-results="#pull-request-search-results" data-live-search-filters="#pull-request-search-filters" data-live-search-default-status="open">
        <input type="hidden" name="status" value="{{status}}">
        <label class="sr-only" for="pull-request-search-input">Search pull requests</label>
        <input id="pull-request-search-input" class="repo-search-input" type="search" name="q" value="{{q}}" placeholder="Search pull requests" autocomplete="off" data-live-search-input>
        <button class="sr-only" type="submit">Search pull requests</button>
      </form>
    <div id="pull-request-search-filters" class="filters" data-live-search-filters>
      <a class="{{'active' if status == 'open' else ''}}" href="{{current_url_with_params(status='open')}}">Open ({{counts["open"]}})</a>
      <a class="{{'active' if status == 'merged' else ''}}" href="{{current_url_with_params(status='merged')}}">Merged ({{counts["merged"]}})</a>
      <a class="{{'active' if status == 'closed' else ''}}" href="{{current_url_with_params(status='closed')}}">Closed ({{counts["closed"]}})</a>
      <a class="{{'active' if status == 'all' else ''}}" href="{{current_url_with_params(status='all')}}">All</a>
      % if q:
        <a href="{{current_url_with_params(q=None)}}">Clear search</a>
      % end
      % if user:
        <a href="/{{repo['owner_username']}}/{{repo['name']}}/pulls/new">New pull request</a>
      % else:
        <a href="/login?next=/{{repo['owner_username']}}/{{repo['name']}}/pulls/new">New pull request</a>
      % end
    </div>
  </div>
  <div id="pull-request-search-results" style="margin-top:25px;" data-live-search-results aria-live="polite">
    % if pull_requests:
      <ul class="issue-list" data-paginated-list>
        % for pr in pull_requests:
          <li>
            <a href="/{{repo['owner_username']}}/{{repo['name']}}/pulls/{{pr['number']}}">#{{pr["number"]}} {{pr["title"]}}</a>
            <span>({{pr["status"]}} from {{pr["source_owner_username"]}}/{{pr["source_repo_name"]}} {{format_ref_label(pr["source_ref_type"], pr["source_ref_name"])}} into {{format_ref_label(pr["target_ref_type"], pr["target_ref_name"])}})</span>
          </li>
        % end
      </ul>
      % include("pagination.tpl", pagination=pagination)
    % else:
      % if q:
        <p class="empty">No {{pull_request_scope}} matching "{{q}}".</p>
      % else:
        <p class="empty">No {{pull_request_scope}}.</p>
      % end
      % include("pagination.tpl", pagination=pagination)
    % end
  </div>
</section>
