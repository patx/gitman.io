% pagination = get("pagination", {})
% if pagination and pagination.get("has_next"):
  <div
    class="pagination"
    data-pagination
    data-next-url="{{current_url_with_page(pagination['next_page'])}}"
    aria-live="polite"
  >
    <span class="pagination-current" data-pagination-status hidden>Loading more...</span>
  </div>
% end
