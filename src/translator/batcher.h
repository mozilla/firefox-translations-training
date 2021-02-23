#ifndef SRC_BERGAMOT_BATCHER_H_
#define SRC_BERGAMOT_BATCHER_H_

#include "batch.h"
#include "common/options.h"
#include "data/corpus_base.h"
#include "definitions.h"
#include "request.h"

#ifdef WITH_PTHREADS
#include "pcqueue.h"
#endif

#include <set>
#include <vector>

namespace marian {
namespace bergamot {
class Batcher {
public:
  explicit Batcher(Ptr<Options> options);

  // RequestSentence incorporates (tentative) notions of priority with each
  // sentence. This method inserts the sentence into the internal data-structure
  // which maintains priority among sentences from multiple concurrent requests.
  void addSentenceWithPriority(RequestSentence &sentence);
  void addWholeRequest(Ptr<Request> request);
#ifdef WITH_PTHREADS
  void produceTo(PCQueue<Batch> &pcqueue);
#endif

  // Loads sentences with sentences compiled from (tentatively) multiple
  // requests optimizing for both padding and priority.
  bool cleaveBatch(Batch &batch);
  bool operator>>(Batch &batch); // alias

private:
  size_t miniBatchWords;
  std::vector<std::set<RequestSentence>> bucket_;
  size_t batchNumber_{0};
};

} // namespace bergamot
} // namespace marian

#endif // SRC_BERGAMOT_BATCHER_H_
