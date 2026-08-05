import { type KeyboardEvent, useId, useRef, useState } from 'react';
import type { ChatStrategyAnswer, ChatStrategyId } from '@/types/chat';
import { ChatComparisonVote } from './ChatComparisonVote';
import { ChatStrategyAnswerPanel } from './ChatStrategyAnswerPanel';

interface ChatComparisonAnswersProps {
  answers: ChatStrategyAnswer[];
  comparisonId?: string;
  includeDeepResearchVote?: boolean;
  showVote?: boolean;
}

const optionLetter = (strategy: ChatStrategyId) => (strategy === 'current_structured' ? 'A' : 'B');
const optionName = (strategy: ChatStrategyId) => `Opción ${optionLetter(strategy)}`;

export const ChatComparisonAnswers = ({
  answers,
  comparisonId,
  includeDeepResearchVote = false,
  showVote = true,
}: ChatComparisonAnswersProps) => {
  const [activeIndex, setActiveIndex] = useState(0);
  const tabs = useRef<Array<HTMLButtonElement | null>>([]);
  const componentId = useId().replace(/:/g, '');
  const isComparison = answers.length > 1;
  const selectedIndex = Math.min(activeIndex, Math.max(answers.length - 1, 0));
  const canVote =
    isComparison &&
    comparisonId !== undefined &&
    answers.every((answer) => !answer.isStreaming && answer.status !== undefined);

  if (answers.length === 0) return null;

  const selectTab = (index: number) => {
    setActiveIndex(index);
    tabs.current[index]?.focus();
  };

  const handleTabKey = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    if (event.key === 'Home') return selectTab(0);
    if (event.key === 'End') return selectTab(answers.length - 1);
    const offset = event.key === 'ArrowRight' ? 1 : -1;
    selectTab((index + offset + answers.length) % answers.length);
  };

  return (
    <div className='flex flex-col gap-4'>
      {isComparison && (
        <div
          role='tablist'
          aria-label='Opciones de respuesta'
          className='grid grid-cols-2 rounded-xl border border-border bg-muted p-1 md:hidden'
        >
          {answers.map((answer, index) => {
            const selected = index === selectedIndex;
            return (
              <button
                key={answer.strategy}
                ref={(node) => {
                  tabs.current[index] = node;
                }}
                id={`${componentId}-tab-${index}`}
                type='button'
                role='tab'
                aria-selected={selected}
                aria-controls={`${componentId}-panel-${index}`}
                tabIndex={selected ? 0 : -1}
                onClick={() => setActiveIndex(index)}
                onKeyDown={(event) => handleTabKey(event, index)}
                className={`rounded-lg px-3 py-2 text-sm font-semibold control-focus ${
                  selected ? 'bg-background text-primary shadow-sm' : 'text-muted-foreground'
                }`}
              >
                {optionName(answer.strategy)}
              </button>
            );
          })}
        </div>
      )}

      <div
        data-testid='comparison-grid'
        className={`grid w-full grid-cols-1 gap-4 ${
          isComparison ? 'md:grid-cols-2' : 'mx-auto max-w-4xl'
        }`}
      >
        {answers.map((answer, index) => {
          const label = optionName(answer.strategy);
          return (
            <ChatStrategyAnswerPanel
              key={answer.strategy}
              answer={answer}
              label={label}
              ariaLabel={`Respuesta de la opción ${optionLetter(answer.strategy)}`}
              id={isComparison ? `${componentId}-panel-${index}` : undefined}
              tabPanel={isComparison}
              className={isComparison && index !== selectedIndex ? 'hidden md:block' : undefined}
            />
          );
        })}
      </div>

      {canVote && showVote && (
        <ChatComparisonVote
          comparisonId={comparisonId}
          includeDeepResearch={includeDeepResearchVote}
        />
      )}
    </div>
  );
};
